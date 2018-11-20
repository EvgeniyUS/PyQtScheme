import os, sys

from configlib import BaseConfig
import log

__all__ = ('initLogFromConfig', 'saveLogConfig', 'LogConfigError')


_handlerClassToType = {
  log.StreamLogHandler: 'stream',
  log.FileLogHandler: 'file',
  log.SysLogHandler: 'syslog'
}


class LogConfigError(Exception):
  pass


def initLogFromConfig(config, configPath='/', logDir=None):
  if not isinstance(config, BaseConfig):
    raise TypeError, "'config' must be 'BaseConfig' instance"
  if not config._caseSensitive:
    raise LogConfigError, "'config' must be case sensitive"
  if not isinstance(configPath, str):
    raise TypeError, "'configPath' must be string"
  logDirChecked = False
  log.shutdown()
  savePath = config.getPath()
  try:
    config.setPath(configPath)
    config.setPath('handlers')
    for handlerName in config.enumerateGroups('.'):
      config.setPath(handlerName)
      handlerType = config.readStr('type')
      if handlerType == 'stream':
        streamName = config.readStr('stream', 'stderr')
        if streamName == 'stdout':
          stream = sys.stdout
        elif streamName == 'stderr':
          stream = sys.stderr
        else:
          raise LogConfigError, \
            "Unsupported stream name '%s'for log handler '%s'. " \
            "Only 'stdout' and 'stderr' streams are supported" % \
            (stream, handlerName)
        try:
          handler = log.StreamLogHandler(stream)
        except Exception, e:
          raise LogConfigError, \
            "Error during creation log handler '%s': %s" % (handlerName, str(e))
      elif handlerType == 'file':
        if not logDirChecked:
          logDirChecked = True
          if logDir is None:
            raise LogConfigError, \
              "Handler '%s': 'logDir' must be specified when 'FileLogHandler' used" % handlerName
          if not isinstance(logDir, str):
            raise TypeError, "'logDir' must be string"
        fileName = config.readStr('fileName')
        if not fileName:
          raise LogConfigError, \
            "File name must be specified for log handler '%s'" % handlerName
        if os.path.split(fileName)[0]:
          raise LogConfigError, \
            "Log handler '%s': path can't be specified for file name" % handlerName
        fileName = os.path.join(logDir, fileName)
        modeStr = config.readStr('mode', '0640')
        try:
          mode = int(modeStr, 8)
          if mode < 0 or mode > 0777:
            raise ValueError
        except:
          raise LogConfigError, \
            "Bad 'mode' value '%s' for log handler '%s'" % (modeStr, handlerName)
        rotatePeriodName = config.readStr('rotatePeriod', 'week')
        try:
          rotatePeriod = log._nameToRotatePeriod[rotatePeriodName]
        except:
          raise LogConfigError, \
            "Bad 'rotatePeriod' value '%s' for log handler '%s'" % \
            (rotatePeriodName, handlerName)
        try:
          maxSize = config.readInt('maxSize', 0)
          if maxSize < 0:
            raise ValueError
        except:
          raise LogConfigError, \
            "Bad 'maxSize' value '%s' for log handler '%s'" % (maxSize, handlerName)
        try:
          backupCount = config.readInt('backupCount', 4)
          if backupCount < 0:
            raise ValueError
        except:
          raise LogConfigError, \
            "Bad 'backupCount' value '%s' for log handler '%s'" % (backupCount, handlerName)
        try:
          needGzip = config.readBool('needGzip', True)
        except:
          raise LogConfigError, \
            "Bad 'needGzip' value '%s' for log handler '%s'" % (needGzip, handlerName)
        try:
          handler = log.FileLogHandler(fileName, mode, rotatePeriod, maxSize,
                                       backupCount, needGzip)
        except Exception, e:
          raise LogConfigError, \
            "Error during creation log handler '%s': %s" % (handlerName, str(e))
      elif handlerType == 'syslog':
        access = config.readStr('access', 'lib')
        if access == 'lib':
          accessMode = log.saLIB
          address = None
        elif access == 'unix':
          accessMode = log.saUNIX
          address = config.readStr('socketName', '/dev/log')
        elif access == 'inet':
          accessMode = log.saINET
          host = config.readStr('host', 'localhost')
          try:
            port = config.readInt('port', log.SYSLOG_UDP_PORT)
            if port < 0 or port > 65535:
              raise ValueError
          except:
            raise LogConfigError, \
              "Bad 'port' value '%s' for log handler '%s'" % (port, handlerName)
          address = (host, port)
        else:
          raise LogConfigError, \
            "Unsupported access type '%s' for log handler '%s'" % \
            (access, handlerName)
        facilityName = config.readStr('facility', 'user')
        try:
          facility = log._nameToFacility[facilityName]
        except:
          raise LogConfigError, \
            "Unsupported facility name '%s' for log handler '%s'" % \
            (facilityName, handlerName)
        try:
          handler = log.SysLogHandler(accessMode, address, facility)
        except Exception, e:
          raise LogConfigError, \
            "Error during creation log handler '%s': %s" % (handlerName, str(e))
      else:
        raise LogConfigError, \
          "Unsupported log handler type: '%s' for log handler '%s'" % \
          (handlerType, handlerName)
      logMask = 0
      for priorityName in config.readStrList('levels'):
        try:
          logMask |= 1 << log._nameToPriority[priorityName]
        except:
          raise LogConfigError, \
            "Bad priority value '%s' for log handler '%s'" % (priorityName, handlerName)
      handler.setLogMask(logMask)
      log.addHandler(handlerName, handler)
      config.setPath('..')
    config.setPath('../loggers')
    for loggerName in config.enumerateGroups('.'):
      config.setPath(loggerName)
      logMask = 0
      for priorityName in config.readStrList('levels'):
        try:
          logMask |= 1 << log._nameToPriority[priorityName]
        except:
          raise LogConfigError, \
            "Bad priority value '%s' for loggger '%s'" % (priorityName, loggerName)
      logger = log.Logger(logMask)
      for handlerName in config.readStrList('handlers'):
        logger.attachHandler(handlerName)
      log.addLogger(loggerName, logger)
      config.setPath('..')
  finally:
    config.setPath(savePath)

def saveLogConfig(config, configPath='/', logDir=None):
  if not isinstance(config, BaseConfig):
    raise TypeError, "'config' must be 'BaseConfig' instance"
  if not config._caseSensitive:
    raise LogConfigError, "'config' must be case sensitive"
  if not isinstance(configPath, str):
    raise TypeError, "'configPath' must be string"
  logDirChecked = False
  savePath = config.getPath()
  try:
    config.setPath(configPath)
    config.setPath('handlers')
    for handlerName in log.enumerateHandlers():
      handler = log.getHandler(handlerName)
      if handler:
        config.setPath(handlerName)
        try:
          handlerType = _handlerClassToType[handler.__class__]
        except:
          raise LogConfigError, \
            "Unsupported log handler class: '%s' for log handler '%s'" % \
            (handler.__class__, handlerName)
        if handlerType == 'stream':
          fileNo = handler._stream.fileno()
          if fileNo == 1:
            config.writeStr('stream', 'stdout')
          elif fileNo == 2:
            config.writeStr('stream', 'stderr')
          else:
            raise LogConfigError, \
              "Unsupported StreamLogHandler for log handler '%s'. " \
              "Only 'stdout' and 'stderr' streams are supported" % handlerName
        elif handlerType == 'file':
          if not logDirChecked:
            logDirChecked = True
            if logDir is None:
              raise LogConfigError, \
                "Handler '%s': 'logDir' must be specified when 'FileLogHandler' used" % handlerName
            if not isinstance(logDir, str):
              raise TypeError, "'logDir' must be string"
            logDir = os.path.normpath(os.path.abspath(logDir))
          fileDir, fileName = os.path.split(handler._baseFileName)
          if fileDir != logDir:
            raise LogConfigError, \
              "Handler '%s': file directory and 'logDir' parameter are different" % handlerName
          config.writeStr('fileName', fileName)
          config.writeStr('mode', oct(handler._mode))
          config.writeStr('rotatePeriod', log._rotatePeriodToName[handler._rotatePeriod])
          config.writeInt('maxSize', handler._maxSize)
          config.writeInt('backupCount', handler._backupCount)
          config.writeBool('needGzip', handler._needGzip)
        elif handlerType == 'syslog':
          config.writeStr('facility', log._facilityToName[handler._facility])
          if handler._accessMode == log.saLIB:
            config.writeStr('access', 'lib')
          elif handler._accessMode == log.saUNIX:
            config.writeStr('access', 'unix')
            config.writeStr('socketName', handler._address)
          elif handler._accessMode == log.saINET:
            config.writeStr('access', 'inet')
            config.writeStr('host', handler._address[0])
            config.writeInt('port', handler._address[1])
        config.writeStr('type', handlerType)
        logMask = handler.getLogMask()
        levelNames = []
        for priority in range(log.LOG_MAX_PRIORITY+1):
          if logMask & (1 << priority):
            levelNames.append(log._priorityToName[priority])
        config.writeStrList('levels', levelNames)
        config.setPath('..')
    config.setPath('../loggers')
    for loggerName in log.enumerateLoggers():
      logger = log.getLogger(loggerName)
      if logger:
        config.setPath(loggerName)
        logMask = logger.getLogMask()
        levelNames = []
        for priority in range(log.LOG_MAX_PRIORITY+1):
          if logMask & (1 << priority):
            levelNames.append(log._priorityToName[priority])
        config.writeStrList('levels', levelNames)
        handlerNames = logger.enumerateAttachedHandlers()
        config.writeStrList('handlers', handlerNames)
        config.setPath('..')
    config.flush()
  finally:
    config.setPath(savePath)
