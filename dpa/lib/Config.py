import socket

import configlib
from IPy import IP
import datetime

class BaseConfig(configlib.BaseConfig):

  def readIPAddr(self, path, default=IP('127.0.0.1')):
    """ read IP address from config """
    if not isinstance(default, IP) or len(default) != 1:
      raise configlib.ConfigTypeError,\
        "default value must be IP instance which present single address,"\
        " entry: '%s' default value: '%s'" % (path, default)
    result = self.readStr(path)
    if not result:
      return default
    else:
      try:
        result = IP(result)
        if len(result) != 1:
          raise ValueError
      except:
        raise configlib.ConfigTypeError,\
          "value must be IP instance which present single address,"\
          " entry: '%s' value: '%s'" % (path, value)
      return result

  def writeIPAddr(self, path, value):
    """ write IP address into config """
    if not isinstance(value, IP) or len(value) != 1:
      raise configlib.ConfigTypeError,\
        "value must be IP instance which present single address,"\
        " entry: '%s' value: '%s'" % (path, value)
    self.writeStr(path, str(value))


  def readIPNet(self, path, default=IP('127.0.0.0/8')):
    """ read IP network from config """
    if not isinstance(default, IP):
      raise configlib.ConfigTypeError,\
        "default value must be IP instance, entry: '%s'"\
        " default value: '%s'" % (path, default)
    result = self.readStr(path)
    if not result:
      return default
    else:
      try:
        result = IP(result)
      except:
        raise configlib.ConfigTypeError,\
          "value must be IP instance, entry: '%s'"\
          " value: '%s'" % (path, result)
      return result

  def writeIPNet(self, path, value):
    """ write IP network into config """
    if not isinstance(value, IP):
      raise configlib.ConfigTypeError,\
        "value must be IP instance, entry: '%s'"\
        " value: '%s'" % (path, value)
    self.writeStr(path, str(value))

  def readHost(self, path, default='localhost'):
    """ read valid host name/address from config """
    if not _isValidHost(default):
      raise configlib.ConfigTypeError,\
        "default value must be valid host name/address, entry: '%s'"\
        " default value: '%s'" % (path, default)
    result = self.readStr(path)
    if not result:
      return default
    else:
      if not _isValidHost(result):
        raise configlib.ConfigTypeError,\
          "value must be valid host name/address, entry: '%s'"\
          " value: '%s'" % (path, result)
      return result

  def writeHost(self, path, value):
    """ write valid host name/address into config """
    if not _isValidHost(value):
      raise configlib.ConfigTypeError,\
        "value must be valid host name/address, entry: '%s'"\
        " value: '%s'" % (path, value)
    self.writeStr(path, str(value))

  def readIPAddrList(self, path, default=[]):
    """ read list of IP addresses from config """
    if type(default) != list and type(default) != tuple:
      raise configlib.ConfigTypeError,\
        "default value must be list or tuple of IP addresses,"\
        " entry: '%s' default value: '%s'" % (path, default)
    for x in default:
      if not isinstance(x, IP) or len(x) != 1:
        raise configlib.ConfigTypeError,\
          "default value must be list or tuple of IP addresses,"\
          " entry: '%s' default value: '%s'"\
          " '%s' is bad" % (path, default, x)
    result = self.readStr(path)
    if not result:
      return default
    else:
      try:
        value = result
        lst = result.split(self._listDelimiter)
      except:
        raise configlib.ConfigTypeError,\
          "value must be list or tuple of IP addresses,"\
          " entry: '%s' value: '%s'" % (path, value)
      try:
        result = [IP(x.strip()) for x in lst]
        for x in result:
          if len(x) != 1:
            raise ValueError
      except:
        raise configlib.ConfigTypeError,\
          "value must be list or tuple of IP addresses,"\
          " entry: '%s' value: '%s'"\
          " '%s' is bad"  % (path, value, x)
      return result

  def writeIPAddrList(self, path, value):
    """ write list of IP addresses into config """
    if type(value) != list and type(value) != tuple:
      raise configlib.ConfigTypeError,\
        "value must be list or tuple of IP addresses,"\
        " entry: '%s' value: '%s'" % (path, value)
    result=[]
    for x in value:
      if not isinstance(x, IP) or len(x) != 1:
        raise configlib.ConfigTypeError,\
          "value must be list or tuple of IP addresses,"\
          " entry: '%s' value: '%s'"\
          " '%s' is bad" % (path, value, x)
      result.append(str(x))
    self.writeStr(path, self._listDelimiter.join(result))

  def readIPNetList(self, path, default=[]):
    """ read list of IP networks from config """
    if type(default) != list and type(default) != tuple:
      raise configlib.ConfigTypeError,\
        "default value must be list or tuple of IP networks,"\
        " entry: '%s' default value: '%s'" % (path, default)
    for x in default:
      if not isinstance(x, IP):
        raise configlib.ConfigTypeError,\
          "default value must be list or tuple of IP networks,"\
          " entry: '%s' default value: '%s'"\
          " '%s' is bad" % (path, default, x)
    result = self.readStr(path)
    if not result:
      return default
    else:
      try:
        value = result
        lst = result.split(self._listDelimiter)
      except:
        raise configlib.ConfigTypeError,\
          "value must be list or tuple of IP networks,"\
          " entry: '%s' value: '%s'" % (path, result)
      try:
        result = [IP(x.strip()) for x in lst]
      except:
        raise configlib.ConfigTypeError,\
          "value must be list or tuple of IP networks,"\
          " entry: '%s' value: '%s'"\
          " '%s' is bad" % (path, value, x)
      return result

  def writeIPNetList(self, path, value):
    """ write list of IP networks into config """
    if type(value) != list and type(value) != tuple:
      raise configlib.ConfigTypeError,\
        "value must be list or tuple of IP addresses,"\
        " entry: '%s' value: '%s'" % (path, value)
    result=[]
    for x in value:
      if not isinstance(x, IP):
        raise configlib.ConfigTypeError,\
          "value must be list or tuple of IP addresses,"\
          " entry: '%s' value: '%s'"\
          " '%s' is bad" % (path, value, x)
      result.append(str(x))
    self.writeStr(path, self._listDelimiter.join(result))

  def readHostList(self, path, default=[]):
    """ read list of valid host names/addresses """
    if type(default) != list and type(default) != tuple:
      raise configlib.ConfigTypeError,\
        "default value must be list or tuple of valid host names/addresses,"\
        " entry: '%s' default value: '%s'" % (path, default)
    for x in default:
      if not _isValidHost(x):
        raise configlib.ConfigTypeError,\
          "default value must be list or tuple of valid host names/addresses,"\
          " entry: '%s' default value: '%s'"\
          " '%s' is bad" % (path, default, x)
    result = self.readStr(path)
    if not result:
      return default
    else:
      try:
        value = result
        lst = result.split(self._listDelimiter)
      except:
        raise configlib.ConfigTypeError,\
          "value must be list or tuple of valid host names/addresses,"\
          " entry: '%s' value: '%s'" % (path, value)
      try:
        result = [x.strip() for x in lst]
        for x in result:
          if not _isValidHost(x):
            raise ValueError
      except:
        raise configlib.ConfigTypeError,\
          "value must be list or tuple of valid host names/addresses,"\
          " entry: '%s' value: '%s'"\
          " '%s' is bad" % (path, value, x)
      return result

  def writeHostList(self, path, value):
    """ write list of valid host names/addresses into config """
    if type(value) != list and type(value) != tuple:
      raise configlib.ConfigTypeError,\
        "value must be list or tuple of valid host names/addresses,"\
        " entry: '%s' value: '%s'" % (path, value)
    result=[]
    for x in value:
      x = str(x)
      if not _isValidHost(x):
        raise configlib.ConfigTypeError,\
          "value must be list or tuple of valid host names/addresses,"\
          " entry: '%s' value: '%s'"\
          " '%s' is bad"  % (path, value, x)
      result.append(x)
    self.writeStr(path, self._listDelimiter.join(result))

  def readDate(self, path, default=datetime.date.min):
    """ read date from config """
    if not isinstance(default, datetime.date):
      raise configlib.ConfigTypeError,\
        "default value must be 'date' class instance,"\
        " entry: '%s' default value: '%s'" % (path, default)
    result = self.readStr(path)
    if not result:
      return default
    else:
      try:
        value = result
        result = datetime.date(int(result[:4]), int(result[5:7]),\
                                                            int(result[8:10]))
      except:
        raise configlib.ConfigTypeError,\
          "value must be 'date' class instance,"\
          " entry: '%s' value: '%s'" % (path, value)
      return result

  def writeDate(self, path, value):
    """ write date into config """
    if not isinstance(value, datetime.date):
      raise configlib.ConfigTypeError,\
        "value must be 'date' class instance,"\
        " entry: '%s' value: '%s'" % (path, value)
    self.writeStr(path, value.strftime('%Y-%m-%d'))

  def readTime(self, path, default=datetime.time.min):
    """ read time from config """
    if not isinstance(default, datetime.time):
      raise configlib.ConfigTypeError,\
        "default value must be 'time' class instance,"\
        " entry: '%s' default value: '%s'" % (path, default)
    result = self.readStr(path)
    if not result:
      return default
    else:
      try:
        value = result
        result = datetime.time(int(result[:2]), int(result[3:5]),\
                                                            int(result[6:8]))
      except:
        raise configlib.ConfigTypeError,\
          "value must be 'time' class instance,"\
          " entry: '%s' value: '%s'" % (path, value)
      return result

  def writeTime(self, path, value):
    """ write time into config """
    if not isinstance(value, datetime.time):
      raise configlib.ConfigTypeError,\
        "value must be 'time' class instance,"\
        " entry: '%s' value: '%s'" % (path, value)
    self.writeStr(path, value.strftime('%H:%M:%S'))

  def readDateTime(self, path, default=datetime.datetime.min):
    """ read datetime from config """
    if not isinstance(default, datetime.datetime):
      raise configlib.ConfigTypeError,\
        "default value must be 'datetime' class instance,"\
        " entry: '%s' default value: '%s'" % (path, default)
    result = self.readStr(path)
    if not result:
      return default
    else:
      try:
        value = result
        result = datetime.datetime(int(result[:4]), int(result[5:7]),\
          int(result[8:10]), int(result[11:13]), int(result[14:16]),\
          int(result[17:19]))
      except:
        raise configlib.ConfigTypeError,\
          "value must be 'datetime' class instance,"\
          " entry: '%s' value: '%s'" % (path, value)
      return result

  def writeDateTime(self, path, value):
    """ write datetime into config """
    if not isinstance(value, datetime.datetime):
      raise configlib.ConfigTypeError,\
        "value must be 'datetime' class instance,"\
        " entry: '%s' value: '%s'" % (path, value)
    self.writeStr(path, value.strftime('%Y-%m-%dT%H:%M:%S'))

def _isValidHost(host):
  try:
    socket.gethostbyname(host)
  except:
    return False
  return True


class Config(configlib._IniMixIn, BaseConfig):
  pass


class XMLConfig(configlib._XMLMixIn, BaseConfig):
  pass
