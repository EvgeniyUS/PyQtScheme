def initLocale():
  import sys, locale
  reload(sys)
  aliases = {'cp1251' : 'windows-1251'}
  encoding = locale.getpreferredencoding().lower()
  encoding = aliases.get(encoding, encoding)
  sys.setdefaultencoding(encoding)
  del sys.setdefaultencoding
  locale.setlocale(locale.LC_ALL, '')
