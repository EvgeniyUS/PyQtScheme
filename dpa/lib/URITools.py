import re

from SharedLock import SharedLock


_noDecodeSymbols = ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    'abcdefghijklmnopqrstuvwxyz'
                    '0123456789_.-/')
_noDecodeDict = {}
for sym in _noDecodeSymbols:
  _noDecodeDict[sym] = None

reURI = re.compile('((?P<scheme>[^:/?#]+):)?'
                   '(//(?P<authority>[^/?#]*))?'
                   '(?P<path>[^?#]*)'
                   '(\?(?P<query>[^#]*))?'
                   '(#(?P<fragment>.*))?')


class _ParsedURICache(object):

  def __init__(self, maxCacheSize):
    self._uriInfo = {}
    self._lock = SharedLock()
    self._maxCacheSize = maxCacheSize

  def getParsedURI(self, uri):
    self._lock.acquireRead()
    try:
      return self._uriInfo[uri]
    finally:
      self._lock.release()

  def addParsedURI(self, uri, parsed):
    self._lock.acquireWrite()
    if len(self._uriInfo) >= self._maxCacheSize:
      self._uriInfo = {}
    self._uriInfo[uri] = parsed
    self._lock.release()


def parseURI(uri):
  global _parsedURICache
  try:
    parsed = _parsedURICache.getParsedURI(uri)
  except KeyError:
    mo = reURI.match(uri)
    parsed = ( mo.group('scheme'),
               mo.group('authority'),
               mo.group('path'),
               mo.group('query'),
               mo.group('fragment')
             )
    _parsedURICache.addParsedURI(uri, parsed)
  return parsed

def splitHost(host):
  pos = host.find(':')
  if pos == -1:
    return host, None
  else:
    hst = host[:pos]
    try:
      port = int(host[pos+1:])
    except:
      raise ValueError, "Port part must be integer"
    return hst, port

def encodePath(s):
  global _noDecodeDict
  res = list(s)
  for i in range(len(res)):
    if not res[i] in _noDecodeDict:
      res[i] = '%%%02X' % ord(res[i])
  return ''.join(res)

def decodePath(s):
  _chr = chr
  _int = int
  lst = s.split('%')
  res = [lst[0]]
  _append = res.append
  del lst[0]
  for item in lst:
    if item[1:2]:
      try:
        _append(_chr(_int(item[:2], 16)) + item[2:])
      except ValueError:
        _append('%' + item)
    else:
      _append('%' + item)
  return "".join(res)

_parsedURICache = _ParsedURICache(200)
