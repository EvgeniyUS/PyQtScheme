################################################################################
##                                                                            ##
## configlib.py                                                               ##
## Module for reading/writing .ini/.conf style config files                   ##
##                                                                            ##
## Author: Mike Rozhnov (scr@incomsys.ru)                                     ##
## Copyright 2000, Mike Rozhnov                                               ##
## License: Python license or GPL                                             ##
##                                                                            ##
## Changes:                                                                   ##
##   version 0.1, 14.02.2000                                                  ##
##     - initial release                                                      ##
##                                                                            ##
##   version 0.2, 01.03.2000                                                  ##
##     - line continuation now is optional                                    ##
##     - added optional header to put in the beginning of file                ##
##                                                                            ##
##   version 0.2.1, 26.06.2000                                                ##
##     - bug with empty values of parameters fixed                            ##
##                                                                            ##
##   version 0.2.2, 26.10.2000                                                ##
##     - enum functions now return relative path name                         ##
##                                                                            ##
##   version 0.2.3, 22.11.2000                                                ##
##     - 'path' parameter for enum functions now has default value            ##
##       (current path)                                                       ##
##     - bug with 'default' parameter in readBoolean and readYesNo fixed      ##
##                                                                            ##
##   version 0.2.4, 24.11.2000                                                ##
##     - bug in _saveFile on unix fixed                                       ##
##     - bug in parse with CR & LF handling on unix fixed                     ##
##                                                                            ##
##   version 0.2.5, 04.01.2001                                                ##
##     - bug in _superstrip fixed                                             ##
##                                                                            ##
##   version 0.2.6, 09.01.2002                                                ##
##     - fixed bug then fileName non exists                                   ##
##                                                                            ##
##   version 0.2.7, 16.05.2004                                                ##
##     - generate and _gen optimizations                                      ##
##                                                                            ##
##   version 0.3, 21.05.2004                                                  ##
##     - new exception - ConfigTypeError (if readXXX functions can't          ##
##       convert to requested type)                                           ##
##     - readBoolean & readYesNo - now return True or False                   ##
##     - extended diagnostic when readXXX functions failed                    ##
##     - more strong type control                                             ##
##     - config literals true, false, yes, no now are case insensitive        ##
##     - readStrList & writeStrList                                           ##
##                                                                            ##
##   version 0.3.1, 25.05.2004                                                ##
##     - mktemp -> TemporaryFile                                              ##
##     - mode argument for config file                                        ##
##                                                                            ##
##   version 0.3.2, 27.05.2004                                                ##
##     - many typos fixed                                                     ##
##                                                                            ##
##   version 0.3.3, 10.11.2004                                                ##
##     - bug in Config.__init__ fixed (skipped param in baseclass constructor)##
##                                                                            ##
##   version 0.3.4, 24.02.2005                                                ##
##     - strip() value in readBool/readYesNo before comparition with literals ##
##                                                                            ##
##   version 0.4, 06.03.2005                                                  ##
##     - new style classes now used                                           ##
##     - _IniMixIn - mix-in for .ini/.conf style Config                       ##
##     - now all is ready to make XMLConfig class                             ##
##     - paths with spaces are accepted now                                   ##
##     - writeFloat value and readFloat default value now can accept int      ##
##       instead float                                                        ##
##                                                                            ##
##   version 0.4.1, 07.03.2005                                                ##
##     - _XMLMixIn - mix-in for XML format Config                             ##
##     - XMLConfig class added                                                ##
##                                                                            ##
##   version 0.5, 07.10.2005                                                  ##
##     - file-like object suppot added, so:                                   ##
##         fileName -> file                                                   ##
##         globalName -> globalFile                                           ##
##         setOutputFileName -> setOutputFile                                 ##
##     - 'file' parameter in constructors can be string, containing name      ##
##       of file or object which has attribute 'read'                         ##
##     - 'globalFile' parameter in constructors can be string, containing     ##
##       name of file or object which has attribute 'read'                    ##
##     - parameter of 'setOutputFile' method can be string, containing name   ##
##       of file or object which has attribute 'write'                        ##
##                                                                            ##
##   version 0.5.1, 20.10.2005                                                ##
##     - check for duplication entries during parse added                     ##
##                                                                            ##
##   version 0.5.2, 21.09.2007                                                ##
##     - function _escape now became method                                   ##
##                                                                            ##
##   version 0.5.3, 03.07.2008                                                ##
##     - _ConfigBase renamed to BaseConfig                                    ##
##     - enumEntries -> enumerateEntries, enumGroups -> enumerateGroups       ##
##                                                                            ##
##   version 0.5.4, 08.08.2008                                                ##
##     - config classes are case sensitive by default now                     ##
################################################################################

__version__ = "0.5.4"

import os, sys, stat
from tempfile import TemporaryFile
from shutil import copyfileobj

T_ENTRY = 0
T_GROUP = 1

class ConfigError(Exception):
  pass

class ConfigValueError(ConfigError):
  pass

class ConfigTypeError(ConfigError):
  pass

class ConfigPathError(ConfigError):
  pass

class ConfigParseError(ConfigError):
  pass

class _ConfigNode:
  def __init__(self, name='', nodeType=T_ENTRY, value=''):
    if name == '' or name in ('/', '.', '..'):
      raise ConfigValueError, "node name can not be empty or '/', '.', '..'"
    else:
      self.name = name
      self.nodeType = nodeType
      if self.nodeType == T_ENTRY:
        if value:
          self.value = value
        else:
          self.value = ''
      else:
        self.value = {}
      self.parent = None

################################################################################
##                          Abstract base config class                        ##
################################################################################

class BaseConfig(object):
  """ Abstract Config class """

  def __init__(self, file=None, globalFile=None, mode=None, autoSave=True,\
                                         caseSensitive=True, listDelimiter=','):
    """Constructor.  May be extended, do not override."""
    self._file = file
    if isinstance(self._file, basestring):
      self._outputFile = self._file
    else:
      self._outputFile = None
    self._globalFile = globalFile
    self._mode = mode
    self._autoSave = autoSave
    self._caseSensitive = caseSensitive
    self._listDelimiter = listDelimiter
    self._isChanged = False
    self._confTree = _ConfigNode('root', T_GROUP)
    self._initConfig()
    self.setRootPath()

################################################################################
##                 Internal file manipulation functions                       ##
################################################################################

  def _getFile(self, iFile):
    data = ''
    if isinstance(iFile, basestring):
      try:
        infile = file(iFile,'r')
        data = infile.read()
        infile.close()
      except:
        pass
    else:
      try:
        data = iFile.read()
      except:
        pass
    return data

  def _saveFile(self, oFile, data):
    if isinstance(oFile, basestring):
      if self._mode:
        mode = self._mode
      else:
        try:
          mode = stat.S_IMODE(os.stat(oFile).st_mode)
        except:
          mode = None
      tmpfile = TemporaryFile()
      tmpfile.write(data)
      tmpfile.seek(0)
      try:
        os.unlink(oFile)
      except:
        pass
      outfile = file(oFile, 'wb')
      copyfileobj(tmpfile, outfile)
      outfile.close()
      if mode:
        try:
          os.chmod(oFile, mode)
        except:
          pass
    else:
      try:
        oFile.write(data)
      except:
        pass

  def _initConfig(self):
    if self._globalFile:
      self.parse(self._getFile(self._globalFile))
    if self._file:
      self.parse(self._getFile(self._file))

  def _update(self):
    self._isChanged = True
    if self._autoSave:
      self.flush()

################################################################################
##                 Internal node manipulation functions                       ##
################################################################################

  def _normalize(self, s):
    if not self._caseSensitive:
      s = s.lower()
    return '/'.join([x.strip() for x in s.split('/')])

  def _getNode(self, path, nodeType, createOnDemand=False):
    path, name = self._splitPath(path)
    if path:
      if path[0] == '/':                 # absolute path
        node = self._confTree
      else:                              # relative path
        node = self._currentPath
      for item in path.split('/'):
        if item == '..':
          if node.parent is None:
            raise ConfigPathError, 'path not found in config'
          else:
            node = node.parent
        elif item != '.' and item != '':
          try:
            node = node.value[(item,T_GROUP)]
          except KeyError:
            if createOnDemand:
               parent = node
               node = _ConfigNode(item,T_GROUP)
               node.parent = parent
               parent.value[(node.name,T_GROUP)] = node
            else:
              raise ConfigPathError, 'path not found in config'
    else:
      node = self._currentPath
    if name:
      try:
        node = node.value[(name,nodeType)]
      except KeyError:
        if createOnDemand and nodeType == T_GROUP:
          parent = node
          node = _ConfigNode(name,T_GROUP)
          node.parent = parent
          parent.value[(node.name,T_GROUP)] = node
        else:
          raise ConfigPathError, 'node not found in config'
    return node

  def _getPath(self, node):
    path = ''
    while True:
      if node.parent is None:
        path = '/' + path
        break
      else:
        path = node.name + '/' + path
        node = node.parent
    if path != '/':
      path = path[:-1]
    return path

  def _splitPath(self, path):
    if path in ('.', '..'):
      return (path, '')
    path = self._normalize(path)
    n = path.rfind('/')
    if n == -1:
      name = path
      path = ''
    elif n == 0:
      name = path[1:]
      path = '/'
    else:
      name = path[n+1:]
      path = path[:n]
    return (path, name)

  def _addNode(self, path, node):
   parent = self._getNode(path, T_GROUP, createOnDemand=True)
   if parent.value.has_key((node.name,node.nodeType)):
      raise ConfigPathError, 'node already exists in config'
   else:
      node.parent = parent
      parent.value[(node.name,node.nodeType)] = node

  def _deleteNode(self, path, nodeType):
    node = self._getNode(path, nodeType)
    if path == '/':       # delete all entries/subgroups for root group
      node.value = {}
    else:
      del node.parent.value[(node.name, nodeType)]
      self._delRecursive(node.parent)
      self._update()

  def _renameNode(self, path, newpath, nodeType):
    if path == '/':  # You can not rename root group
      raise ConfigValueError, 'can not rename root group'
    node = self._getNode(path, nodeType)
    key = node.name, nodeType
    parent = node.parent
    newpath, name = self._splitPath(newpath)
    if name:
      node.name = name
    self._addNode(newpath, node)
    del parent.value[key]
    self._delRecursive(node.parent)
    self._update()

  def _writeNode(self, path, value, replaceAllowed=False):
    if type(path) != str:
      raise ConfigTypeError, "entry path must be string,"\
                             " entered path: '%s'" % path
    if type(value) != str:
      raise ConfigTypeError,\
        "value must be string, entry: '%s' value: '%s'" % (path, value)
    value = value.strip()
    parentpath, name = self._splitPath(path)
    if not name:
      raise ConfigPathError,\
                    "you must specify entry name in path,"\
                    " entered path: '%s'" % path
    parent = self._getNode(parentpath, T_GROUP, createOnDemand=True)
    if parent.value.has_key((name, T_ENTRY)):
      if replaceAllowed:
        node = self._getNode(path, T_ENTRY)
        node.name = name
        node.value = value
      else:
        raise ConfigValueError, "entry duplicated in config: '%s'" % path
    else:
      self._addNode(parentpath, _ConfigNode(name, T_ENTRY, value))
    self._update()

  def _delRecursive(self, node):
    while len(node.value) == 0:
      if node.parent:
        name = node.name
        node = node.parent
        del node.value[(name, T_GROUP)]
        self._currentPath = node
      else:
        break

  def _enumNode(self, path, nodeType, recursive=False, pathPrefix=''):
    if not self.hasGroup(path):
      raise ConfigPathError, 'can not enumerate entry (group only)'
    result = []
    node = self._getNode(path, T_GROUP)
    for key in node.value.keys():
      val = node.value[key]
      if val.nodeType == nodeType:
        result.append(self._normalize(pathPrefix + val.name))
      if recursive and val.nodeType == T_GROUP:
        result = result + \
          self._enumNode(self._getPath(val), \
          nodeType, recursive, self._normalize(pathPrefix + val.name + '/'))
    return result

################################################################################
##                           Path managment                                   ##
################################################################################

  def setRootPath(self):
    """ Set current path in config to root """
    self._currentPath = self._confTree

  def setPath(self, path):
    """ Set current path in config """
    self._currentPath = self._getNode(path, T_GROUP, createOnDemand=True)

  def getPath(self):
    """ Return current path in config """
    node = self._currentPath
    return self._getPath(node)

################################################################################
##                          Tests of existence                                ##
################################################################################

  def hasGroup(self, path):
    """ Return true if such group exists """
    try:
      self._getNode(path, T_GROUP)
    except ConfigPathError:
      return False
    return True

  def hasEntry(self, path):
    """ Return true if such entry exists """
    try:
      self._getNode(path, T_ENTRY)
    except ConfigPathError:
      return False
    return True

################################################################################
##                   Node manipulation functions                              ##
################################################################################

  def deleteGroup(self, path):
    """ Delete group from config.
        For root path delete all children entries.
    """
    self._deleteNode(path, T_GROUP)

  def renameGroup(self, path, newpath):
    """ Rename/move group in config """
    self._renameNode(path, newpath, T_GROUP)

  def enumerateGroups(self, path='', recursive=False):
    """ Return list of paths of all subgroups relative to 'path' """
    return self._enumNode(path, T_GROUP, recursive)

  def deleteEntry(self, path):
    """ Delete entry from config. """
    self._deleteNode(path, T_ENTRY)

  def renameEntry(self, path, newpath):
    """ Rename/move entry in config """
    self._renameNode(path, newpath, T_ENTRY)

  def enumerateEntries(self, path='', recursive=False):
    """ Return list of paths of all entries in group relative to 'path' """
    return self._enumNode(path, T_ENTRY, recursive)

################################################################################
##                        Write config functions                              ##
################################################################################

  def writeStr(self, path, value):
    """ write string into config """
    self._writeNode(path, value, replaceAllowed=True)

  def writeInt(self, path, value):
    """ write integer into config """
    if type(value) != int:
      raise ConfigTypeError,\
        "value must be integer, entry: '%s' value: '%s'" % (path, value)
    self.writeStr(path, str(value))

  def writeFloat(self, path, value):
    """ write float into config """
    if type(value) == int:
      value = float(value)
    if type(value) != float:
      raise ConfigTypeError,\
        "value must be float, entry: '%s' value: '%s'" % (path, value)
    self.writeStr(path, str(value))

  def writeBool(self, path, value):
    """ write boolean into config """
    if type(value) != bool and type(value) != int:
      raise ConfigTypeError,\
        "value must be boolean or integer, entry: '%s'"\
        " value: '%s'" % (path, value)
    if value:
      s = 'True'
    else:
      s = 'False'
    self.writeStr(path, s)
  writeBoolean = writeBool # compatibility

  def writeYesNo(self, path, value):
    """ write 'yes' or 'no' into config """
    if type(value) != bool and type(value) != int:
      raise ConfigTypeError,\
        "value must be boolean or integer, entry: '%s'"\
        " value: '%s'" % (path, value)
    if value:
      s = 'yes'
    else:
      s = 'no'
    self.writeStr(path, s)

  def writeStrList(self, path, value):
    """ write list of strings into config """
    if type(value) != list and type(value) != tuple:
      raise ConfigTypeError,\
        "value must be list or tuple of strings, entry: '%s'"\
        " value: '%s'" % (path, value)
    result=[]
    for x in value:
      if type(x) != str:
        raise ConfigTypeError,\
          "value must be list or tuple of strings, entry: '%s'"\
          " value: '%s'" % (path, value)
      result.append(x.strip())
    self.writeStr(path, self._listDelimiter.join(result))

################################################################################
##                         Read config functions                              ##
################################################################################
  def readStr(self, path, default=''):
    """ read string from config """
    if type(default) != str:
      raise ConfigTypeError,\
        "default value must be string, entry: '%s'"\
        " default value: '%s'" % (path, default)
    try:
      node = self._getNode(path, T_ENTRY)
    except ConfigPathError:
      return default
    return node.value

  def readInt(self, path, default=0):
    """ read integer from config """
    if type(default) != int:
      raise ConfigTypeError,\
        "default value must be integer, entry: '%s'"\
        " default value: '%s'" % (path, default)
    result = self.readStr(path)
    if not result:
      return default
    else:
      try:
        result = int(result)
      except:
        raise ConfigTypeError,\
          "value must be integer, entry: '%s' value: '%s'" % (path, result)
      return result

  def readFloat(self, path, default=0.0):
    """ read float from config """
    if type(default) == int:
      default = float(default)
    if type(default) != float:
      raise ConfigTypeError,\
        "default value must be float, entry: '%s'"\
        " default value: '%s'" % (path, default)
    result = self.readStr(path)
    if not result:
      return default
    else:
      try:
        result = float(result)
      except:
        raise ConfigTypeError,\
          "value must be float, entry: '%s' value: '%s'" % (path, result)
      return result

  def readBool(self, path, default=False):
    """ read boolean from config """
    if not isinstance(default, bool):
      raise ConfigTypeError,\
        "default value must be bool, entry: '%s'"\
        " default value: '%s'" % (path, default)
    result = self.readStr(path).lower()
    if not result:
      return default
    elif result == 'true':
      return True
    elif result == 'false':
      return False
    else:
      raise ConfigTypeError,\
        "value must be 'true' or 'false' literal, entry: '%s'"\
        " value: '%s'" % (path, result)
  readBoolean = readBool # compatibility

  def readYesNo(self, path, default='no'):
    """ read 'yes' or 'no' from config """
    try:
      default = default.lower()
      if default != 'yes' and default != 'no':
        raise ValueError
    except:
      raise ConfigTypeError,\
        "default value must be 'yes' or 'no' literal, entry: '%s'"\
        " default value: '%s'" % (path, default)
    result = self.readStr(path).lower()
    if not result:
      result = default
    if result == 'yes':
      return True
    elif result == 'no':
      return False
    else:
      raise ConfigTypeError,\
        "value must be 'yes' or 'no' literal, entry: '%s'"\
        " value: '%s'" % (path, result)

  def readStrList(self, path, default=[]):
    """ read list of strings from config """
    if type(default) != list and type(default) != tuple:
      raise ConfigTypeError,\
        "default value must be list or tuple of strings, entry: '%s'"\
        " default value: '%s'" % (path, default)
    for x in default:
      if type(x) != str:
        raise ConfigTypeError,\
          "default value must be list or tuple of strings, entry: '%s'"\
          " default value: '%s'" % (path, default)
    result = self.readStr(path)
    if not result:
      return default
    else:
      try:
        result = [x.strip() for x in result.split(self._listDelimiter)]
      except:
        raise ConfigTypeError,\
          "value must be list or tuple of strings, entry: '%s'"\
          " value: '%s'" % (path, result)
      return result

################################################################################
##                       File manipulation functions                          ##
################################################################################
  def flush(self):
    """ Use flush to save changes to file. Don't override. """
    if self._isChanged:
      if self._outputFile:
        self._saveFile(self._outputFile, self.generate())
        self._isChanged = False
      else:
        raise ConfigError, 'output file name not specified'

  def setOutputFile(self, oFile):
    """ Set output file (name or file object) """
    self._outputFile = oFile

################################################################################
##                     Functions to override in derived classes               ##
################################################################################

  def parse(self, data):
    pass

  def generate(self):
    return ''

################################################################################
##                      .ini/.conf style config mix-in                        ##
################################################################################

class _IniMixIn(object):
  """ .ini/.conf style config mix-in """

  def __init__(self, file=None, globalFile=None, mode=None, autoSave=False, \
               caseSensitive=True, listDelimiter=',', delimiter='=', \
               comment='#', linecont=None, header=None):
    """Constructor.  May be extended, do not override."""
    self._delimiter = self._escape(delimiter)
    self._comment = comment
    self._linecont = self._escape(linecont)
    self._header = header
    super(_IniMixIn, self).__init__(file, globalFile, mode, autoSave, \
                                                   caseSensitive, listDelimiter)

  def parse(self, data):
    import re
    from cStringIO import StringIO

    _GROUP_STR = re.compile(
      r'\s*\[\s*(?P<gr_name>\S.*?)\s*]\s*$'        #group name
    )
    if not self._linecont:
      _OPT_STR = re.compile(
        r'\s*(?P<key>\S.*?)\s*'+                     #entry name
        self._delimiter +                            #delimiter
        r'(?P<value>.*)'                             #value
      )
    else:
      _OPT_STR = re.compile(
        r'\s*(?P<key>\S.*?)\s*'+                     #entry name
        self._delimiter +                            #delimiter
        r'(?P<value>.*?)'                            #value
        r'(?P<c_flag>' + self._linecont + r'\s*?)?$' #continuation flag
      )
      _OPT_CONT_STR = re.compile(
        r'(?P<value>.*?)'                            #value
        r'(?P<c_flag>' + self._linecont + r'\s*?)?$' #continuation flag
      )

    cur_grp = ''
    f = StringIO(data)
    line = f.readline()
    linenum = 1
    while line:
      line = self._superstrip(line)
      if line:
        m = _GROUP_STR.match(line)
        if m:
          cur_grp = '/' + m.group('gr_name')
        else:
          m = _OPT_STR.match(line)
          if m:
            key = '/' + m.group('key')
            value = m.group('value')
            if self._linecont:
              cont = m.group('c_flag')
              while cont:
                line = f.readline()
                linenum += 1
                line = self._superstrip(line)
                if not line:
                  raise ConfigParseError, \
                    'line continuation not found, line number:' + str(linenum)
                else:
                  m = _OPT_CONT_STR.match(line)
                  if m:
                    value += m.group('value')
                    cont = m.group('c_flag')
                  else:
                    raise ConfigParseError, \
                      'line continuation not found, line number:' + str(linenum)
            try:
              self._writeNode(cur_grp+key, value)
            except ConfigValueError, e:
              raise ConfigParseError, \
                              '%s, line number: %s' % (e.args[0], str(linenum))
          else:
            raise ConfigParseError, \
              'line not expected, line number:' + str(linenum)
      line = f.readline()
      linenum += 1
    f.close()

  def generate(self):
    data = ''
    if self._header:
      lst = self._header.split('\n')
      nlst = []
      for s in lst:
        nlst.append('%s %s' % (self._comment, s))
      data = '\n'.join(nlst)+'\n'
    return self._gen('/', data)

  def _gen(self, path, data):
    lst = self.enumerateEntries(path)
    if len(lst):
      lst.sort()
      nlst = []
      if path == '/':
        for val in lst:
          nlst.append('%s%s%s' % (val, self._delimiter, self.readStr('/' + val)))
        data = '%s%s\n' % (data, '\n'.join(nlst))
      else:
        if data:
          data = '%s\n[%s]\n' % (data, path[1:])
        else:
          data = '[%s]\n' % path[1:]
        for val in lst:
          nlst.append('%s%s%s' % (val, self._delimiter, \
                                               self.readStr(path + '/' + val)))
        data = '%s%s\n' % (data, '\n'.join(nlst))
    lst = self.enumerateGroups(path)
    lst.sort()
    for val in lst:
      if path == '/':
        data = self._gen('/' + val, data)
      else:
        data = self._gen(path + '/' + val, data)
    return data

  def _superstrip(self, line):
    pos = line.find(self._comment)
    if pos != -1:
      line = line[:pos]
    return line.strip()

  def _escape(self, value):
    if value:
      lst = list(value)
      for i in range(len(lst)):
        if lst[i] in r'.^$*+?{[\|()':
          lst[i] = '\\'+lst[i]
      value = ''.join(lst)
    return value


################################################################################
##                                XML config mix-in                           ##
################################################################################

class _XMLMixIn(object):
  """ XML config mix-in """

  def __init__(self, file=None, globalFile=None, mode=None, autoSave=False, \
               caseSensitive=True, listDelimiter=',', encoding=None, \
                                                         indent=2, header=None):
    """Constructor.  May be extended, do not override."""
    self.defaultEncoding = sys.getdefaultencoding()
    if not encoding:
      self._encoding = self.defaultEncoding
    else:
      self._encoding = encoding
    self._indent = indent
    self._header = header
    super(_XMLMixIn, self).__init__(file, globalFile, mode, autoSave, \
                                                   caseSensitive, listDelimiter)

  def parse(self, data):
    from xml.parsers import expat
    parser = expat.ParserCreate()
    parser.StartElementHandler = self._startTagHandler
    parser.EndElementHandler = self._endTagHandler
    self._curPathLst = []
    try:
      parser.Parse(data)
    except Exception, e:
      raise ConfigParseError, str(e)
    del self._curPathLst

  def generate(self):
    data = []
    if self._encoding != 'utf-8': # default for xml
      data.append("<?xml version='1.0' encoding='%s'?>" % self._encoding)
    else:
      data.append("<?xml version='1.0'?>")
    if self._header:
      hLst = self._header.split('\n')
      modLst = []
      for line in hLst:
        if self.defaultEncoding != self._encoding:
          line = line.decode(self.defaultEncoding).encode(self._encoding)
        modLst.append(self._escape(line))
      data.append('<!-- %s -->' % '\n     '.join(modLst))
    data.append('<config>')
    data = self._gen('/', data)
    data.append("</config>")
    return '\n'.join(data)

  def _startTagHandler(self, tag, attrs):
    if tag == 'group':
      self._curPathLst.append(str(attrs['name']))
    elif tag == 'parameter':
      path = '/' +  '/'.join(self._curPathLst) + '/' + str(attrs['name'])
      self._writeNode(path, str(attrs['value']))

  def _endTagHandler(self, tag):
    if tag == 'group':
      del self._curPathLst[-1]

  def _gen(self, path, data, offs=1):
    offset = ' ' * offs * self._indent
    lst = self.enumerateEntries(path)
    if len(lst):
      lst.sort()
      if path == '/':
        for val in lst:
          s = self.readStr('/' + val)
          if self.defaultEncoding != self._encoding:
            s = s.decode(self.defaultEncoding).encode(self._encoding)
          val = self._escape(val)
          s = self._escape(s)
          data.append(offset + "<parameter name='%s' value='%s'/>" % (val, s))
      else:
        for val in lst:
          s = self.readStr(path + '/' + val)
          if self.defaultEncoding != self._encoding:
            s = s.decode(self.defaultEncoding).encode(self._encoding)
          val = self._escape(val)
          s = self._escape(s)
          data.append(offset + "<parameter name='%s' value='%s'/>" % (val, s))
    lst = self.enumerateGroups(path)
    lst.sort()
    for val in lst:
      if path == '/':
        data.append(offset + "<group name='%s'>" % val)
        data = self._gen('/' + val, data, offs+1)
        data.append(offset + "</group>")
      else:
        data.append(offset + "<group name='%s'>" % val)
        data = self._gen(path + '/' + val, data, offs+1)
        data.append(offset + "</group>")
    return data

  def _escape(self, value):
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

################################################################################
##                    Config class (.ini/.conf style config)                  ##
################################################################################

class Config(_IniMixIn, BaseConfig):
  """ Config class (.ini/.conf style config) """

################################################################################
##                              XMLConfig class                               ##
################################################################################

class XMLConfig(_XMLMixIn, BaseConfig):
  """ XMLConfig class """

################################################################################
##                                     Test                                   ##
################################################################################

def _test():
  head = "This file was generated by configlib (version=%s).\n" % __version__ +\
         "Please don't edit manualy!"
  conf = Config(header=head)
  conf.writeStr('/a', 'string')
  conf.writeStr('/abc/a', 'Long parameter   with   spaces')
  conf.writeStr('/abc/def/a', 'Another parameter')
  conf.writeInt('/b', 12)
  conf.writeFloat('/c', 23.3)
  conf.writeBoolean('/d', 1)
  conf.writeBoolean('/e', False)
  conf.writeStrList('/e', ('abc','def','ghi'))
  conf.writeInt('/a/b/c/d/e/f/g', 12)
  print 'All variables in config:'
  for s in conf.enumerateEntries('/',recursive=1):
    print s, '=', conf.readStr(s)
  conf.setPath('/a/b/c/d/e/f')
  print 'curent path -', conf.getPath()
  print "Before deleting 'g' conf.hasGroup('/a') return",
  if conf.hasGroup('/a'):
    print 'true'
  else:
    print 'false'
  conf.deleteEntry('g')  # automaticaly delete empty parent groups
  print "After deleting 'g' conf.hasGroup('/a') return",
  if conf.hasGroup('/a'):
    print 'true'
  else:
    print 'false'
  print "curent path after deleting 'g' -", conf.getPath()
  conf.setOutputFile('test.ini')
  print "saving config in 'test.ini'"
  conf.flush()
  print "parsing 'test.ini'"
  conf = Config('test.ini', header=head)
  print "All variables in 'test.ini':"
  for s in conf.enumerateEntries('/',recursive=1):
    print s, '=', conf.readStr(s)
  print "result of conf.readInt('/b')*2 =", conf.readInt('/b')*2
  print "result of conf.readFloat('/b')*2 =", conf.readFloat('/b')*2
  print "result of conf.readFloat('/c')*2 =", conf.readFloat('/c')*2
  print conf.readStrList('/e')


################################################################################
##                                   __main__                                 ##
################################################################################

if __name__ == '__main__':
  _test()
