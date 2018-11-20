import sys
from encodings import normalize_encoding, aliases

cyrillicEncodings = ('cp866', 'cp1251', 'iso8859_5', 'koi8_r', 'utf_8')

def canonicalName(enc):
  enc = normalize_encoding(enc.lower())
  return aliases.aliases.get(enc, enc)

def isCyrillic(enc):
  return canonicalName(enc) in cyrillicEncodings

defaultEncoding = canonicalName(sys.getdefaultencoding())
if defaultEncoding not in cyrillicEncodings:
  raise ValueError, "Default encoding is not cyrillic encoding"

def convertCyrillic(encoding='koi8-r'):
  encoding = canonicalName(encoding)
  if encoding not in cyrillicEncodings:
    raise ValueError, "'%s' is not cyrillic encoding" % encoding
  if encoding == defaultEncoding:
    return lambda x: x
  else:
    return lambda x: str(x.decode(encoding))
