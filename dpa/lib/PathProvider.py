import os, sys, re

# Application types
atCLIENT = 1
atSERVER = 2

# Application's location - meaningful for Unix'es only
# for FHS conformance
alCOMMON = 1       # /usr
alSYSTEM = 2       # /
alOPT_PACKAGE = 3  # /opt/<package>
alOPT_VENDOR = 4   # /opt/<vendor>/<package>

join = os.path.join

if sys.platform.startswith('win'):
  confExt = '.ini'
else:
  confExt = '.conf'


class PathProviderError(Exception):
  pass


class PathProvider(object):
  def __init__(self, appType=atCLIENT, appLocation=alCOMMON, vendor=None, appName=None):
    if appLocation == alOPT_VENDOR:
      if not vendor or not isinstance(vendor, str):
        raise ValueError, "'vendor' must be non-empty string"
    if not appName:
      appName = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    else:
      if not isinstance(appName, str):
        raise TypeError, "'appName' must be string or None"
    self._paths = {}
    self._paths['appName'] = appName
    if sys.platform.startswith('win'):
      if sys.getwindowsversion()[3] < 2:
        raise RuntimeError, "Windows 3.1/95/98/ME are not supported"
      appPath = os.path.split(os.path.abspath(sys.argv[0]))[0]
      self._paths['sysConfigDir'] = os.environ["SystemRoot"]
      self._paths['appConfigDir'] = join(appPath, 'Config')
      self._paths['appConfigFile'] = join(self.sysConfigDir, appName + confExt)
      self._paths['appLibDir'] = join(appPath, 'Lib')
      self._paths['appPluginsDir'] = join(appPath, 'Plugins')
      self._paths['appDataDir'] = join(appPath, 'Data')
      self._paths['appVarDataDir'] = join(appPath, 'Data')
      self._paths['appLogDir'] = join(appPath, 'Log')
      self._paths['appDocDir'] = join(appPath, 'Doc')
      self._paths['appSpoolDir'] = join(appPath, 'Spool')
      if appType == atCLIENT:
        self._paths['userHomeDir'] = os.environ["USERPROFILE"]
        self._paths['userAppDataDir'] = join(os.environ["APPDATA"],  appName)
        self._paths['userAppConfigFile'] = join(self.userAppDataDir, appName + confExt)
    else:
      self._paths['sysConfigDir'] = '/etc'
      if appLocation in (alCOMMON, alSYSTEM):
        if appLocation == alCOMMON:
          subPath = '/usr'
        else: # alSYSTEM
          subPath = '/'
        self._paths['appConfigDir'] = join('/etc', appName)
        self._paths['appConfigFile'] = join('/etc', appName + confExt)
        libDir = join(subPath, 'lib', appName)
        self._paths['appLibDir'] = libDir
        self._paths['appPluginsDir'] = join(libDir, 'plugins')
        self._paths['appDataDir'] = join('/usr/share', appName)
        self._paths['appVarDataDir'] = join('/var/lib', appName)
        self._paths['appLogDir'] = join('/var/log', appName)
        self._paths['appDocDir'] = join('/usr/share/doc', appName)
        self._paths['appSpoolDir'] = join('/var/spool', appName)
      else: # alOPT_PACKAGE, alOPT_VENDOR
        if appLocation == alOPT_PACKAGE:
          subPath = join('opt', appName)
        else: # alOPT_VENDOR
          subPath = join('opt', vendor, appName)
        self._paths['appConfigDir'] = join('/etc', subPath)
        self._paths['appConfigFile'] = join('/etc', subPath) + confExt
        libDir = join('/', subPath, 'lib')
        self._paths['appLibDir'] = libDir
        self._paths['appPluginsDir'] = join(libDir, 'plugins')
        self._paths['appDataDir'] = join('/', subPath, 'data')
        self._paths['appVarDataDir'] = join('/var', subPath, 'data')
        self._paths['appLogDir'] = join('/var', subPath, 'log')
        self._paths['appDocDir'] = join('/', subPath, 'share/doc')
        self._paths['appSpoolDir'] = join('/var', subPath, 'spool')
      if appLocation == alOPT_VENDOR:
        self._paths['vendorConfigDir'] = join('/etc/opt', vendor)
      if appType == atCLIENT:
        self._paths['userHomeDir'] = os.path.expanduser('~')
        self._paths['userAppDataDir'] = join(self.userHomeDir, '.' + appName)
        self._paths['userAppConfigFile'] = join(self.userHomeDir, '.' + appName + confExt)

    self._paths['generateSysConfigFile'] = lambda name: join(self.sysConfigDir, name + confExt)
    self._paths['generateAppConfigFile'] = lambda name: join(self.appConfigDir, name + confExt)
    if appLocation == alOPT_VENDOR and not sys.platform.startswith('win'):
      self._paths['generateVendorConfigFile'] = lambda name: join(self.vendorConfigDir, name + confExt)
    if appType == atCLIENT:
      if sys.platform.startswith('win'):
        self._paths['generateUserAppConfigFile'] = lambda name: join(self.userAppDataDir, name + confExt)
        self._paths['generateUserConfigFile'] = lambda name: join(self.userHomeDir, name + confExt)
      else:
        self._paths['generateUserAppConfigFile'] = lambda name: join(self.userAppDataDir, '.' + name + confExt)
        self._paths['generateUserConfigFile'] = lambda name: join(self.userHomeDir, '.' + name + confExt)

  def  __getattr__(self, name):
    if name == '_paths':
      return super(PathProvider, self).__getattr__(name)
    try:
      return self._paths[name]
    except KeyError:
      raise AttributeError, "'%s' object has no attribute '%s'" % \
                                                (self.__class__.__name__, name)

  def  __setattr__(self, name, value):
    if name == '_paths' and not hasattr(self, '_paths'):
      super(PathProvider, self).__setattr__(name, value)
    else:
      raise AttributeError, "can't set attribute"
