import os, sys, time
import socket
import glob, gzip
import re
import threading
import atexit
from datetime import date, timedelta

try:
  import syslog
except ImportError:
  syslog = None

from SharedLock import SharedLock

isIdentifier = re.compile(r'^[a-zA-Z]([a-zA-Z0-9_])*$').match

saLIB = 1
saUNIX = 2
saINET = 3

syslogAccessModes = (saLIB, saUNIX, saINET)

SYSLOG_UDP_PORT = 514

# syslog priorities

LOG_EMERG     = 0       #  system is unusable
LOG_ALERT     = 1       #  action must be taken immediately
LOG_CRIT      = 2       #  critical conditions
LOG_ERR       = 3       #  error conditions
LOG_WARNING   = 4       #  warning conditions
LOG_NOTICE    = 5       #  normal but significant condition
LOG_INFO      = 6       #  informational
LOG_DEBUG     = 7       #  debug-level messages

LOG_MAX_PRIORITY = LOG_DEBUG

priorities = (
  LOG_EMERG,
  LOG_ALERT,
  LOG_CRIT,
  LOG_ERR,
  LOG_WARNING,
  LOG_NOTICE,
  LOG_INFO,
  LOG_DEBUG
)

_priorityToName = {
  LOG_EMERG : 'emergency',
  LOG_ALERT : 'alert',
  LOG_CRIT : 'critical',
  LOG_ERR : 'error',
  LOG_WARNING : 'warning',
  LOG_NOTICE : 'notice',
  LOG_INFO : 'info',
  LOG_DEBUG : 'debug'
}

_nameToPriority = {}
for key, val in _priorityToName.items():
  _nameToPriority[val] = key


# syslog facilities

LOG_KERN      = 0       #  kernel messages
LOG_USER      = 1       #  random user-level messages
LOG_MAIL      = 2       #  mail system
LOG_DAEMON    = 3       #  system daemons
LOG_AUTH      = 4       #  security/authorization messages DEPRECATED
LOG_SYSLOG    = 5       #  messages generated internally by syslogd
LOG_LPR       = 6       #  line printer subsystem
LOG_NEWS      = 7       #  network news subsystem
LOG_UUCP      = 8       #  UUCP subsystem
LOG_CRON      = 9       #  clock daemon
LOG_AUTHPRIV  = 10      #  security/authorization messages (private)
#  other codes through 15 reserved for system use
LOG_LOCAL0    = 16      #  reserved for local use
LOG_LOCAL1    = 17      #  reserved for local use
LOG_LOCAL2    = 18      #  reserved for local use
LOG_LOCAL3    = 19      #  reserved for local use
LOG_LOCAL4    = 20      #  reserved for local use
LOG_LOCAL5    = 21      #  reserved for local use
LOG_LOCAL6    = 22      #  reserved for local use
LOG_LOCAL7    = 23      #  reserved for local use

facilities = (
LOG_KERN,
LOG_USER,
LOG_MAIL,
LOG_DAEMON,
LOG_AUTH,
LOG_SYSLOG,
LOG_LPR,
LOG_NEWS,
LOG_UUCP,
LOG_CRON,
LOG_AUTHPRIV,
LOG_LOCAL0,
LOG_LOCAL1,
LOG_LOCAL2,
LOG_LOCAL3,
LOG_LOCAL4,
LOG_LOCAL5,
LOG_LOCAL6,
LOG_LOCAL7
)

_facilityToName = {
LOG_KERN: 'kern',
LOG_USER: 'user',
LOG_MAIL: 'mail',
LOG_DAEMON: 'daemon',
LOG_AUTH: 'auth',
LOG_SYSLOG: 'syslog',
LOG_LPR: 'lpr',
LOG_NEWS: 'news',
LOG_UUCP: 'uucp',
LOG_CRON: 'cron',
LOG_AUTHPRIV: 'authpriv',
LOG_LOCAL0: 'local0',
LOG_LOCAL1: 'local1',
LOG_LOCAL2: 'local2',
LOG_LOCAL3: 'local3',
LOG_LOCAL4: 'local4',
LOG_LOCAL5: 'local5',
LOG_LOCAL6: 'local6',
LOG_LOCAL7: 'local7'
}

_nameToFacility = {}
for key, val in _facilityToName.items():
  _nameToFacility[val] = key


rpNONE = 0
rpDAY = 1
rpWEEK = 2
rpMONTH = 3
rpQUARTER = 4
rpHALFYEAR = 5
rpYEAR = 6

rotatePeriods = (rpNONE, rpDAY, rpWEEK, rpMONTH, rpQUARTER, rpHALFYEAR, rpYEAR)

_rotatePeriodToName = {
  rpNONE: 'none',
  rpDAY: 'day',
  rpWEEK: 'week',
  rpMONTH: 'month',
  rpQUARTER: 'quarter',
  rpHALFYEAR: 'halfyear',
  rpYEAR: 'year'
}

_nameToRotatePeriod = {}
for key, val in _rotatePeriodToName.items():
  _nameToRotatePeriod[val] = key

_FILE_SUFFIX_RE = re.compile('^\.(?P<count>[0-9]+)(?P<gz>(\.gz)?)$')

_lock = SharedLock()
_handlerRegistry = {}
_loggerRegistry = {}
_priorityToHint = {}

def logMask(priority):
  if priority not in priorities:
    raise ValueError, "bad 'priority' value"
  return 1 << priority

def logMaskUpTo(priority):
  if priority not in priorities:
    raise ValueError, "bad 'priority' value"
  return (1 << (priority + 1)) - 1

lmALL = logMaskUpTo(LOG_DEBUG)

def setPriorityHint(priority, hint):
  if priority not in priorities:
    raise ValueError, "bad 'priority' value"
  if hint is not None and not isinstance(hint, str):
    raise ValueError, "'hint' must be string or None"
  _lock.acquireWrite()
  if hint:
    _priorityToHint[priority] = hint
  else:
    try:
      del _priorityToHint[priority]
    except:
      pass
  _lock.release()

def getPriorityHint(priority):
  if priority not in priorities:
    raise ValueError, "bad 'priority' value"
  _lock.acquireRead()
  try:
    hint = _priorityToHint[priority]
  except:
    hint = _priorityToName[priority]
  _lock.release()
  return hint

def addHandler(name, handler):
  _lock.acquireWrite()
  try:
    if not isinstance(name, str):
      raise TypeError, "'name' must be string"
    if not isIdentifier(name):
      raise ValueError, "bad 'name' value"
    if not isinstance(handler, BaseLogHandler):
      raise TypeError, "'handler' must be 'BaseLogHandler' instance"
    if name in _handlerRegistry:
      raise ValueError, "Handler name '%s' is duplicated" % name
    _handlerRegistry[name] = handler
  finally:
    _lock.release()

def deleteHandler(name):
  _lock.acquireWrite()
  try:
    del _handlerRegistry[name]
  except:
    pass
  else:
    for logger in _loggerRegistry:
      logger.detachHandler(name)
  _lock.release()

def enumerateHandlers():
  _lock.acquireRead()
  handlers = _handlerRegistry.keys()
  _lock.release()
  return handlers

def getHandler(name):
  _lock.acquireRead()
  try:
    handler = _handlerRegistry[name]
  except:
    handler = None
  _lock.release()
  return handler

def addLogger(name, logger=None):
  _lock.acquireWrite()
  try:
    if not isinstance(name, str):
      raise TypeError, "'name' must be string"
    if not isIdentifier(name):
      raise ValueError, "bad 'name' value"
    if name in _loggerRegistry:
      raise ValueError, "logger '%s' already registered" % name
    if logger is None:
      logger = Logger()
    elif not isinstance(logger, Logger):
      raise ValueError, "'logger' must be 'Logger' instnace or None"
    _loggerRegistry[name] = logger
  finally:
    _lock.release()

def deleteLogger(name):
  _lock.acquireWrite()
  try:
    del _loggerRegistry[name]
  except:
    pass
  _lock.release()

def enumerateLoggers():
  _lock.acquireRead()
  logList = _loggerRegistry.keys()
  _lock.release()
  return logList

def getLogger(name):
  _lock.acquireRead()
  try:
    logger = _loggerRegistry[name]
  except:
    logger = None
  _lock.release()
  return logger

def log(loggerName, priority, msg, *args):
  logger = getLogger(loggerName)
  if logger and logger.getLogMask() & logMask(priority):
    msgStr = msg % args
    timeStamp = time.time()
    logFields = _makeLogFields(loggerName, priority, msgStr)
    for handlerName in logger.enumerateAttachedHandlers():
      handler = getHandler(handlerName)
      if handler and handler.getLogMask() & logMask(priority):
        handler.handleMessage(timeStamp, logFields)

def emergency(loggerName, msg, *args):
  log(loggerName, LOG_EMERG, msg, *args)

def alert(loggerName, msg, *args):
  log(loggerName, LOG_ALERT, msg, *args)

def critical(loggerName, msg, *args):
  log(loggerName, LOG_CRIT, msg, *args)

def error(loggerName, msg, *args):
  log(loggerName, LOG_ERR, msg, *args)

def warning(loggerName, msg, *args):
  log(loggerName, LOG_WARNING, msg, *args)

def notice(loggerName, msg, *args):
  log(loggerName, LOG_NOTICE, msg, *args)

def info(loggerName, msg, *args):
  log(loggerName, LOG_INFO, msg, *args)

def debug(loggerName, msg, *args):
  log(loggerName, LOG_DEBUG, msg, *args)

def _makeLogFields(loggerName, priority, message):
  logFields = {}
  logFields['loggerName'] = loggerName
  logFields['priority'] = priority
  logFields['priorityName'] = _priorityToName[priority]
  logFields['priorityNameUpper'] = _priorityToName[priority].upper()
  logFields['priorityHint'] = getPriorityHint(priority)
  logFields['message'] = message
  logFields['processId'] = os.getpid()
  return logFields

def shutdown():
  for loggerName in enumerateLoggers():
    deleteLogger(loggerName)
  for handlerName in enumerateHandlers():
    deleteHandler(handlerName)

atexit.register(shutdown)


class Logger(object):

  def __init__(self, logMask=lmALL):
    self._handlers = {}
    self._lock = SharedLock()
    self.setLogMask(logMask)

  def setLogMask(self, logMask=lmALL):
    if not isinstance(logMask, int) or logMask < 0 or logMask > lmALL:
      raise ValueError, "'logMask' must be integer between 0 and 0x%X" % lmALL
    self._logMask = logMask

  def getLogMask(self):
    return self._logMask

  def attachHandler(self, handlerName):
    if handlerName not in enumerateHandlers():
      raise ValueError, "handler '%s' is not registered" % handlerName
    self._lock.acquireWrite()
    self._handlers[handlerName] = None
    self._lock.release()

  def detachHandler(self, handlerName):
    self._lock.acquireWrite()
    try:
      del self._handlers[handlerName]
    except:
      pass
    self._lock.release()

  def enumerateAttachedHandlers(self):
    self._lock.acquireRead()
    handlers = self._handlers.keys()
    self._lock.release()
    return handlers


class BaseLogHandler(object):

  DEFAULT_FORMAT = "%(timeStamp)s %(message)s"
  DEFAULT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

  def __init__(self):
    self._lock = threading.Lock()
    self._logMask = lmALL
    self._format = self.DEFAULT_FORMAT
    self._timeFormat = self.DEFAULT_TIME_FORMAT

  def __del__(self):
    self.close()

  def setLogMask(self, logMask=lmALL):
    if not isinstance(logMask, int) or logMask < 0 or logMask > lmALL:
      raise ValueError, "'logMask' must be integer between 0 and 0x%X" % lmALL
    self._logMask = logMask

  def setFormat(self, format=""):
    if not isinstance(format, str):
      raise ValueError, "'format' must be string"
    if format:
      self._format = format
    else:
      self._format = self.DEFAULT_FORMAT

  def setTimeFormat(self, timeFormat=""):
    if not isinstance(timeFormat, str):
      raise ValueError, "'timeFormat' must be string"
    if timeFormat:
      self._timeFormat = timeFormat
    else:
      self._timeFormat = self.DEFAULT_TIME_FORMAT

  def getLogMask(self):
    return self._logMask

  def handleMessage(self, timeStamp, fields):
    timeStampStr = self.formatTimeStamp(timeStamp)
    fields['timeStamp'] = timeStampStr
    self._lock.acquire()
    try:
      self.writeMessage(fields)
    finally:
      self._lock.release()

  def formatMessage(self, fields):
    return self._format % fields

  def formatTimeStamp(self, timeStamp):
    return time.strftime(self._timeFormat, time.localtime(timeStamp))

  def writeMessage(self, fields):
    raise NotImplementedError, "'writeMessage' method is not implemented"

  def close(self):
    pass


class StreamLogHandler(BaseLogHandler):

  def __init__(self, stream=None):
    super(StreamLogHandler, self).__init__()
    if stream:
      if hasattr(stream, 'write'):
        self._stream = stream
      else:
        raise ValueError, "'stream' must have 'write' attribute"
      if hasattr(stream, 'flush'):
        self._hasFlush = True
      else:
        self._hasFlush = False
    else:
      self._stream = sys.stderr
      self._hasFlush = True

  def flush(self):
    if self._hasFlush:
      self._stream.flush()

  def writeMessage(self, fields):
    msg = self.formatMessage(fields)
    self._stream.write(msg + '\n')
    self.flush()

  def close(self):
    self.flush()


class FileLogHandler(StreamLogHandler):

  def __init__(self, fileName, mode=0640, rotatePeriod=rpWEEK, maxSize=0,
                                                  backupCount=4, needGzip=True):
    self._closed = False
    self._fileName = fileName
    self._stream = file(fileName, 'a+')
    super(FileLogHandler, self).__init__(self._stream)
    self._baseFileName = os.path.normpath(os.path.abspath(fileName))
    self._statusFile = self._baseFileName + '.status'
    self._mode = mode
    try:
      os.chmod(self._baseFileName, self._mode)
    except:
      pass
    if rotatePeriod not in rotatePeriods:
      raise ValueError, "bad 'rotatePeriod' value"
    self._rotatePeriod = rotatePeriod
    self._maxSize = maxSize
    self._backupCount = backupCount
    self._needGzip = needGzip
    self._gzipThread = None
    self._readCreateLogDate()
    self._nextBackup = self._computeNextBackup()
    if self._nextBackup and date.today() >= self._nextBackup:
      self._doRollOver()

  def _doRollOver(self):
    if self._needGzip and self._gzipThread:
      self._gzipThread.join()
      self._gzipThread = None
    self._stream.close()
    if self._backupCount > 0:
      lbfn = len(self._baseFileName)
      rl = glob.glob(self._baseFileName + '*')
      fl = []
      for fName in rl:
        if fName == self._baseFileName:
          fl.append((fName, 0, False))
        else:
          m = _FILE_SUFFIX_RE.match(fName[lbfn:])
          if m:
            count = int(m.group('count'))
            if m.group('gz'):
              appendGzipSuffix = True
            else:
              appendGzipSuffix = False
            fl.append((fName, count, appendGzipSuffix))

      fl.sort(key=lambda x: x[1], reverse=True) # for right rename order
      for fName, count, appendGzipSuffix in fl:
        if count < self._backupCount:
          newFileName = '%s.%d' % (self._baseFileName, count+1)
          if appendGzipSuffix:
            newFileName += '.gz'
          os.rename(fName, newFileName)
        else:
          os.remove(fName)
      if self._needGzip:
        self._startGzipLastBackup()
    else:
      os.remove(self._baseFileName)
    self._stream = file(self._baseFileName, 'a+')
    try:
      os.chmod(self._baseFileName, self._mode)
    except:
      pass
    self._writeCreateLogDate()
    self._readCreateLogDate()
    self._nextBackup = self._computeNextBackup()

  def _computeNextBackup(self):
    ld = self.createLogDate
    if self._rotatePeriod == rpNONE:
      nb = None
    elif self._rotatePeriod == rpDAY:
      nb = ld + timedelta(1)
    elif self._rotatePeriod == rpWEEK:
      nb = ld + timedelta(7 - ld.weekday())
    elif self._rotatePeriod == rpMONTH:
      year = ld.year
      month = ld.month + 1
      if month > 12:
        month = 1
        year = year + 1
      nb = date(year, month, 1)
    elif self._rotatePeriod == rpQUARTER:
      year = ld.year
      month = ld.month
      if month in (1, 2, 3):
        month = 4
      elif month in (4, 5, 6):
        month = 7
      elif month in (7, 8, 9):
        month = 10
      else:
        month = 1
        year = year + 1
      nb = date(year, month, 1)
    elif self._rotatePeriod == rpHALFYEAR:
      year = ld.year
      month = ld.month
      if month in (1, 2, 3, 4, 5, 6):
        month = 7
      else:
        month = 1
        year = year + 1
      nb = date(year, month, 1)
    elif self._rotatePeriod == rpYEAR:
      nb = date(ld.year+1, 1, 1)
    else:
      nb = None
    return nb

  def _writeCreateLogDate(self):
    try:
      sf = file(self._statusFile, 'w')
      sf.write(date.today().strftime('%Y-%m-%d'))
      sf.close()
    except:
      pass
    try:
      os.chmod(self._statusFile, self._mode)
    except:
      pass

  def _readCreateLogDate(self):
    try:
      sf = file(self._statusFile, 'r')
      status = sf.read()
      sf.close()
      y = int(status[0:4])
      m = int(status[5:7])
      d = int(status[8:10])
      self.createLogDate = date(y, m, d)
    except:
      self.createLogDate = date.today()
      self._writeCreateLogDate()

  def writeMessage(self, msgStr):
    if self._nextBackup and date.today() >= self._nextBackup:
      self._doRollOver()
    elif self._maxSize:
      self._stream.seek(0, 2)  #due to non-posix-compliant Windows feature
      if self._stream.tell() + len(msgStr) >= self._maxSize:
        self._doRollOver()
    super(FileLogHandler, self).writeMessage(msgStr)

  def _startGzipLastBackup(self):
    self._gzipThread = threading.Thread(target=self._gzipLastBackup)
    self._gzipThread.start()

  def _gzipLastBackup(self):
    sz = 64*1024
    fo = file(self._baseFileName + '.1', 'rb')
    fn = file(self._baseFileName + '.1.gz', 'wb')
    p,n = os.path.split(self._baseFileName)
    g = gzip.GzipFile(n, 'wb', 9, fn)
    data = fo.read(sz)
    while data:
      g.write(data)
      data = fo.read(sz)
    g.close()
    fn.close()
    fo.close()
    os.remove(self._baseFileName + '.1')

  def close(self):
    if not self._closed:
      try:
        if self._nextBackup and date.today() >= self._nextBackup:
          self._doRollOver()
        super(FileLogHandler, self).close()
      except:
        pass
      try:
        self._stream.close()
      except:
        pass
      self._closed = True


class SysLogHandler(BaseLogHandler):

  DEFAULT_FORMAT = "%(message)s"

  def __init__(self, access=saLIB, address=None, facility=LOG_USER):
    # default address:
    #  - for glibc access - n/a
    #  - address=('localhost', SYSLOG_UDP_PORT) for udp socket send to local or remote syslog
    #  - address='/dev/log' for local syslog
    super(SysLogHandler, self).__init__()
    if access not in syslogAccessModes:
      raise ValueError, "bad 'access' value"
    if access==saLIB and syslog is None or \
       access==saUNIX and sys.platform.startswith('win'):
      raise ValueError, "access mode not supported on this platform"
    self._accessMode = access
    if facility in facilities:
      self._facility = facility
    else:
      raise ValueError, "bad 'facility' value"
    self._execName = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    if self._accessMode == saLIB:
      syslog.openlog(self._execName)
    elif self._accessMode == saUNIX:
      self._useUnixSocket = True
      if not address:
        address = '/dev/log'
      if not isinstance(address, str):
        raise TypeError, "bad type for 'address'"
      self._connectUnixSocket(address)
    elif self._accessMode == saINET:
      self._useUnixSocket = False
      if not address:
        address = ('localhost', SYSLOG_UDP_PORT)
      if isinstance(address, str):
        address = (address, SYSLOG_UDP_PORT)
      else:
        if not isinstance(address, (tuple, list)):
          raise TypeError, "bad type for 'address'"
      self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    self._address = address
    if self._accessMode == saLIB:
      self.writeMessage = self._writeByStdLib
    else:
      self.writeMessage = self._writeToSocket

  def _connectUnixSocket(self, address):
    self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
      self._socket.connect(address)
    except socket.error:
      self._socket.close()
      self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
      self._socket.connect(address)

  def _writeToSocket(self, fields):
    msg = self.formatMessage(fields)
    logMsg = '<%d>%s: %s\000' % ((self._facility << 3) | fields['priority'], self._execName, msg)
    try:
      if self._useUnixSocket:
        try:
          self._socket.send(logMsg)
        except socket.error:
          self._connectUnixSocket(self._address)
          self._socket.send(logMsg)
      else:
        self._socket.sendto(logMsg, self._address)
    except:
      pass

  def _writeByStdLib(self, fields):
    msg = self.formatMessage(fields)
    syslog.syslog((self._facility << 3) | fields['priority'], msg)

  def close (self):
    if self._useUnixSocket:
      self._socket.close()
    super(SysLogHandler, self).close()
