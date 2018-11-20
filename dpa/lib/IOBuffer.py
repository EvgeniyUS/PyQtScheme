from StringIO import StringIO
from tempfile import TemporaryFile

class IOBuffer(object):

  memBufMaxLen = 131072 #128K

  def __init__(self, startSize=0):
    if startSize > self.memBufMaxLen:
      self.dataobj = TemporaryFile()
      self.isStrBuf = False
    else:
      self.dataobj = StringIO()
      self.isStrBuf = True
    self._internalWrite = self.dataobj.write
    self._internalWriteLines = self.dataobj.writelines

  def __del__(self):
    try:
      self.close()
    except:
      pass

  def _convertBuf(self):
    self.dataobj.seek(0)
    newbuf = TemporaryFile()
    newbuf.write(self.dataobj.read())
    self.dataobj = newbuf
    self._internalWrite = self.dataobj.write
    self._internalWriteLines = self.dataobj.writelines
    self.isStrBuf = False

  def __len__(self):
    if self.isStrBuf:
      return self.dataobj.len
    else:
     savepos = self.tell()
     self.seek(0, 2)
     endpos = self.tell()
     self.seek(savepos)
     return endpos

  _s = "def %s(self, *args): return self.dataobj.%s(*args)\n\n"
  for _m in ('next', 'close', 'flush', 'seek', 'tell', 'truncate',
             'read', 'readline', 'readlines'):
    exec _s % (_m, _m)
  del _m, _s

  def write(self, s):
    if self.isStrBuf:
      if len(self) + len(s) > self.memBufMaxLen:
        self._convertBuf()
    self._internalWrite(s)

  def writelines(self, seq):
    if self.isStrBuf:
      add_len = sum([len(s) for s in seq])
      if len(self) + add_len > self.memBufMaxLen:
        self._convertBuf()
    self._internalWriteLines(seq)
