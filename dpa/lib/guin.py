import os, zlib, random, time, struct

_crc = zlib.crc32(os.environ['PATH']) & 0xffffffff

try:
  _rand = random.SystemRandom()
except:
  _rand = random.Random()

def _random():
  return _rand.randrange(0, 0x10000)

class GUIN:
  """Global universal identification number"""

  def __init__(self, guin=None):
    """If guin is None then generate new GUIN,
       elif guin is string representation of guin then convert it to GUIN
       else raise exception"""
    if guin is None:
      self.__val = (long(time.time()) & 0xffffffff, _crc, _random())
    elif isinstance(guin, str):
      try:
        n1, n2, n3 = guin.split("-")
        if len(n1) != 8 or len(n2) != 8 or len(n3) != 4:
          raise ValueError, "incorrect string presentation of GUIN"
        self.__val = (int(n1, 16), int(n2, 16), int(n3, 16))
      except ValueError:
        raise ValueError, "incorrect string presentation of GUIN"
    elif isinstance(guin, GUIN):
      self.__val = guin.__val
    else:
      raise TypeError, "'guin' must be string, GUIN instance or None"

  def __str__(self):
    """Convert GUIN to string representation"""
    return "%08X-%08X-%04X" % self.__val

  def __cmp__(self, other):
    """Compare GUIN with another GUIN or string presentation of GUIN"""
    if isinstance(other, GUIN):
      return cmp(self.__val, other.__val)
    elif isinstance(other, str):
      return self.__cmp__(GUIN(other))
    else:
      raise TypeError, "incorrect type of operand"
