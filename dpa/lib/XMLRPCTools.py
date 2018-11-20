#
#  XMLRPCTools.py based on code from xmlrpclib.py
#  Copyright (c) 2004 Mike D. Rozhnov
#
#  Original copyright:
#
# Copyright (c) 1999-2002 by Secret Labs AB
# Copyright (c) 1999-2002 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.
# --------------------------------------------------------------------

import sys
import datetime
import base64
import copy
from xml.parsers import expat
from cStringIO import StringIO

from IOBuffer import IOBuffer

# xmlrpc integer limits
MAXINT =  2L**31-1
MININT = -2L**31

defaultEncoding = sys.getdefaultencoding()

def escape(s):
  return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class XMLRPCToolsError(Exception): pass

class XMLRPCParseError(XMLRPCToolsError): pass

class XMLRPCParseEncodingError(XMLRPCParseError): pass

class XMLRPCParseDataTypeError(XMLRPCParseError): pass

class XMLRPCParseValueError(XMLRPCParseError): pass

class XMLRPCGenerateError(XMLRPCToolsError): pass

class XMLRPCGenerateEncodingError(XMLRPCGenerateError): pass

class XMLRPCGenerateDataTypeError(XMLRPCGenerateError): pass

class XMLRPCGenerateValueError(XMLRPCGenerateError): pass

class Fault(XMLRPCToolsError):
  """Indicates an XML-RPC fault package"""

  def __init__(self, faultCode, faultString=''):
    XMLRPCToolsError.__init__(self)
    self.faultCode = faultCode
    self.faultString = faultString

  def __repr__(self):
    return "<Fault %s: %s>" % (self.faultCode, str(self.faultString))

  __str__ = __repr__


class XMLRPCParser:

  parseBase64ToFileObject = False
  temporaryFileObjectClass = None

  skipTagsTuple = ('methodCall', 'methodResponse', 'value', 'param', 'member', 'data')
  skipTags = {}
  for t in skipTagsTuple:
    skipTags[t] = None
  compositeTags = ('struct', 'array')
  dataTagsTuple = ('i4', 'int', 'boolean', 'string', 'double', 'dateTime.iso8601', 'base64',
                   'name', 'methodName')
  dataTags = {}
  for t in dataTagsTuple:
    dataTags[t] = None

  def __init__(self, stream):
    if self.parseBase64ToFileObject and not self.temporaryFileObjectClass:
      raise ValueError, "'fileObjectClass' must be specified"
    parser = expat.ParserCreate()
    parser.StartElementHandler = self.start
    parser.EndElementHandler = self.end
    parser.CharacterDataHandler = self.data
    parser.XmlDeclHandler = self.xml
    parser.buffer_text = True
    self._parser = parser
    self._stream = stream
    self._encoding = 'utf-8'
    self._methodname = None
    self._params = None
    self._type = None
    self._stack = []
    self._marks = []
    self._tag_stack = []
    self._current_tag = None
    self._data = None
    self._b64rest = ''
    self.append = self._stack.append

  def parse(self):
    try:
      self._parser.ParseFile(self._stream)
      del self._parser # get rid of circular references
    except Exception, e:
      del self._parser
      if isinstance(e, XMLRPCParseError):
        raise
      else:
        raise XMLRPCParseError, str(e)
    if self._marks:
      raise XMLRPCParseError, 'Unexpected end of file'

  def getMethodName(self):
    return self._methodname

  def getParams(self):
    if self._type is None:
      params = ()
    elif self._type == 'params':
      params = tuple(self._stack)
    else:
      raise XMLRPCParseError, 'Unexpected params type'
    return params

  def getEncoding(self):
    return self._encoding

  def getResult(self):
    if self._type == 'fault':
      raise Fault(self._stack[0]['faultCode'], self._stack[0]['faultString'])
    elif self._type == 'params':
      result = self._stack[0]
    else:
      raise XMLRPCParseError, 'Unexpected result type'
    return result

  def xml(self, version, encoding, standalone):
    if encoding:
      self._encoding = str(encoding)

  def start(self, tag, attrs):
    if tag in self.compositeTags:
      self._marks.append(len(self._stack))
    elif tag == 'base64':
      if self.parseBase64ToFileObject:
        self._data = self.temporaryFileObjectClass()
      else:
        self._data = []
      self._b64rest = ''
      self._b64error = False # workaround for Python crash when raising Exception
    elif tag in self.dataTags:
      self._data = []
    elif tag in self.dispatch:
      self._data = None
    elif tag not in self.skipTags:
      raise XMLRPCParseDataTypeError, "Unknown XMLRPC type: '%s'" % tag
    self._tag_stack.append(self._current_tag)
    self._current_tag = tag

  def data(self, text):
    if self._current_tag == 'base64':
      if not self._b64error: # workaround for Python crash when raising Exception
        self._b64rest += ''.join(text.split('\n'))
        pos=len(self._b64rest) & 0x7ffffffc
        try: # workaround for Python crash when raising Exception
          decodedStr = base64.b64decode(self._b64rest[:pos])
          self._b64rest = self._b64rest[pos:]
          if self.parseBase64ToFileObject:
            self._data.write(decodedStr)
          else:
            self._data.append(decodedStr)
        except:
          self._b64error = True
    elif self._current_tag in self.dataTags:
      self._data.append(text)

  def end(self, tag):
    # call the appropriate end tag handler
    if tag != self._current_tag:
      raise XMLRPCParseError, "Expected end of '%s', received end of '%s' tag" % \
            (self._current_tag, tag)
    try:
      f = self.dispatch[tag]
    except KeyError:
      if tag not in self.skipTags:
        raise XMLRPCParseDataTypeError, "Unknown XMLRPC type: '%s'" % tag
    else:
      if self._current_tag == 'base64':
        if self._b64error: # workaround for Python crash when raising Exception
          raise XMLRPCParseError, "Bad 'base64' tag"
        if self._b64rest:
          decodedStr = base64.b64decode(self._b64rest)
          self._b64rest = ''
          if self.parseBase64ToFileObject:
            self._data.write(decodedStr)
          else:
            self._data.append(decodedStr)
        if self.parseBase64ToFileObject:
          self._data.seek(0)
          f(self, self._data)
        else:
          f(self, buffer(''.join(self._data)))
      elif self._current_tag in self.dataTags:
        try:
          f(self, ''.join(self._data))
        except XMLRPCParseError:
          raise
        except Exception, e:
          raise XMLRPCParseValueError, str(e)
      else:
        f(self)
      self._data = None
    self._current_tag = self._tag_stack.pop()

  dispatch = {}

  def load_boolean(self, data):
    if data == '0':
      self.append(False)
    elif data == '1':
      self.append(True)
    else:
      raise XMLRPCParseValueError, 'Bad boolean value'
  dispatch['boolean'] = load_boolean

  def load_int(self, data):
    self.append(int(data))
  dispatch['i4'] = load_int
  dispatch['int'] = load_int

  def load_double(self, data):
    self.append(float(data))
  dispatch['double'] = load_double

  def load_string(self, data):
    try:
      self.append(str(data))
    except UnicodeError:
      raise XMLRPCParseEncodingError, "Can't encode unicode string"
  dispatch['string'] = load_string
  dispatch['name'] = load_string # struct keys are always strings

  def load_base64(self, data):
    self.append(data)
  dispatch['base64'] = load_base64

  def load_dateTime(self, data):
    year, month, day = int(data[:4]), int(data[4:6]), int(data[6:8])
    hour, minute, second = int(data[9:11]), int(data[12:14]), int(data[15:17])
    self.append(datetime.datetime(year, month, day, hour, minute, second))
  dispatch['dateTime.iso8601'] = load_dateTime

  def load_methodName(self, data):
    self._methodname = str(data)
  dispatch['methodName'] = load_methodName

  def load_array(self):
    mark = self._marks.pop()
    # map arrays to Python lists
    self._stack[mark:] = [self._stack[mark:]]
  dispatch['array'] = load_array

  def load_struct(self):
    mark = self._marks.pop()
    # map structs to Python dictionaries
    items = self._stack[mark:]
    dct = {}
    for i in range(0, len(items), 2):
      dct[str(items[i])] = items[i+1]
    self._stack[mark:] = [dct]
  dispatch['struct'] = load_struct

  def load_params(self):
    self._type = 'params'
  dispatch['params'] = load_params

  def load_fault(self):
    self._type = 'fault'
  dispatch['fault'] = load_fault


class FileObjectXMLRPCParser(XMLRPCParser):

  parseBase64ToFileObject = True
  temporaryFileObjectClass = IOBuffer


class XMLRPCGenerator:

  def __init__(self, stream, encoding=None):
    self._stream = stream
    if encoding is None:
      self._encoding = 'utf-8'
    else:
      self._encoding = encoding
    self._memo = {}

  def generateRequest(self, method, params):
    if params is not None and not isinstance(params, tuple):
      params = (params,)
    self.dump_header()
    self._stream.write("<methodCall>\n<methodName>%s</methodName>\n" % method)
    if params:
      self.dumps(params)
    self._stream.write("</methodCall>\n")

  def generateResponse(self, result):
    if isinstance(result, tuple) and len(result) != 1:
      result = (result,)
    self.dump_header()
    self._stream.write("<methodResponse>\n")
    self.dumps(result)
    self._stream.write("</methodResponse>\n")

  def dump_header(self):
    if self._encoding != "utf-8": # default for xml
      self._stream.write("<?xml version='1.0' encoding='%s'?>\n" % self._encoding)
    else:
      self._stream.write("<?xml version='1.0'?>\n")

  def dumps(self, values):
    if hasattr(values, 'faultCode') and hasattr(values, 'faultString'):
      # fault instance
      self._stream.write('<fault>\n')
      self.dump_value({'faultCode': values.faultCode,
                       'faultString': values.faultString})
      self._stream.write('</fault>\n')
    else:
      if not isinstance(values, tuple):
        values = (values,)
      self._stream.write('<params>\n')
      for v in values:
        self._stream.write('<param>\n')
        self.dump_value(v)
        self._stream.write('</param>\n')
      self._stream.write('</params>\n')

  def dump_value(self, value):
    try:
      self.dispatch[type(value)](self, value)
    except KeyError:
      raise XMLRPCGenerateDataTypeError, "Can't dump value of type '%s'" % type(value)
  dispatch = {}

  def dump_int(self, value):
    # in case ints are > 32 bits
    if value > MAXINT or value < MININT:
      raise XMLRPCGenerateValueError, \
            'XML-RPC int must be between %d and %d' % (MININT, MAXINT)
    self._stream.write('<value><int>%d</int></value>\n' % value)
  dispatch[int] = dump_int
  dispatch[long] = dump_int

  def dump_bool(self, value):
    self._stream.write('<value><boolean>%d</boolean></value>\n' % value)
  dispatch[bool] = dump_bool

  def dump_double(self, value):
    self._stream.write('<value><double>%.10f</double></value>\n' % value)
  dispatch[float] = dump_double

  def dump_string(self, value):
    if defaultEncoding != self._encoding:
      try:
        newValue = value.decode(defaultEncoding)
      except UnicodeError:
        raise XMLRPCGenerateEncodingError, "Can't decode string to unicode"
      try:
        newValue = newValue.encode(self._encoding)
      except UnicodeError:
        raise XMLRPCGenerateEncodingError, "Can't encode unicode string"
    else:
      newValue = value
    self._stream.write('<value><string>%s</string></value>\n' % escape(newValue))
  dispatch[str] = dump_string

  def dump_unicode(self, value):
    try:
      self._stream.write('<value><string>%s</string></value>\n' % escape(value.encode(self._encoding)))
    except UnicodeError:
      raise XMLRPCGenerateEncodingError, "Can't encode unicode string"
  dispatch[unicode] = dump_unicode

  def dump_buffer(self, value):
    self._stream.write('<value><base64>%s</base64></value>\n' % base64.b64encode(value))
  dispatch[buffer] = dump_buffer

  def dump_datetime(self, value):
    self._stream.write('<value><dateTime.iso8601>%04d%02d%02dT%02d:%02d:%02d</dateTime.iso8601></value>\n' % \
      (value.year, value.month, value.day, value.hour, value.minute, value.second))
  dispatch[datetime.datetime] = dump_datetime

  def dump_date(self, value):
    self._stream.write('<value><dateTime.iso8601>%04d%02d%02dT00:00:00</dateTime.iso8601></value>\n' % \
      (value.year, value.month, value.day))
  dispatch[datetime.date] = dump_date

  def dump_time(self, value):
    self._stream.write('<value><dateTime.iso8601>00010101T%02d:%02d:%02d</dateTime.iso8601></value>\n' % \
      (value.hour, value.minute, value.second))
  dispatch[datetime.time] = dump_time

  def dump_array(self, value):
    i = id(value)
    if i in self._memo:
      raise XMLRPCGenerateDataTypeError, "Can't marshal recursive sequences"
    self._memo[i] = None
    self._stream.write('<value><array><data>\n')
    for v in value:
      self.dump_value(v)
    self._stream.write('</data></array></value>\n')
    del self._memo[i]
  dispatch[tuple] = dump_array
  dispatch[list] = dump_array

  def dump_struct(self, value):
    i = id(value)
    if i in self._memo:
      raise XMLRPCGenerateDataTypeError, "Can't marshal recursive dictionaries"
    self._memo[i] = None
    self._stream.write('<value><struct>\n')
    for key in value:
      self._stream.write('<member>\n')
      if type(key) == str:
        if defaultEncoding != self._encoding:
          newKey = key.decode(defaultEncoding).encode(self._encoding)
        else:
          newKey = key
      elif type(key) == unicode:
        newKey = key.encode(self._encoding)
      else:
        raise XMLRPCGenerateDataTypeError, 'Dictionary key must be string or unicode'
      self._stream.write('<name>%s</name>\n' % escape(newKey))
      self.dump_value(value[key])
      self._stream.write('</member>\n')
    self._stream.write('</struct></value>\n')
    del self._memo[i]
  dispatch[dict] = dump_struct


class FileObjectXMLRPCGenerator(XMLRPCGenerator):

  bufLen = 8192//3*3 # for base64 without padding

  dispatch = copy.copy(XMLRPCGenerator.dispatch)
  del dispatch[buffer]

  def dump_fileObject(self, value):
    self._stream.write('<value><base64>')
    while True:
      s = value.read(self.bufLen)
      if not s:
        break
      while len(s) < self.bufLen:
        ns = value.read(self.bufLen-len(s))
        if not ns:
          break
          s += ns
      self._stream.write(base64.b64encode(s))
    self._stream.write('</base64></value>\n')
  dispatch[file] = dump_fileObject
  dispatch[type(StringIO())] = dump_fileObject
  dispatch[type(StringIO(''))] = dump_fileObject
  dispatch[IOBuffer] = dump_fileObject
