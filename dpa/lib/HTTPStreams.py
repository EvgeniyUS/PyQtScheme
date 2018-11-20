class IdentityIStream(object):

  name = "<IdentityIStream>"

  __slots__ = ("_stream", "_remain", "_check_size", "_eof", "_fileno")

  def __init__(self, stream, streamSize=-1):
    self._stream = stream
    self._fileno = self._stream.fileno()
    if streamSize < 0:
      self._remain = 0
      self._check_size = False
    else:
      self._remain = streamSize
      self._check_size = True
    self._eof = False

  closed = property(lambda self: self._stream is None)

  eof = property(lambda self: self._eof)

  def _check_closed(self):
    if self._stream is None:
      raise ValueError, "Stream is closed"

  def close(self):
    if self._stream is not None:
      self._stream = None

  def __del__(self):
    self.close()

  def fileno(self):
    return self._fileno

  def read(self, size=-1):
    self._check_closed()
    if self._eof or size == 0: return ""
    if self._check_size:
      if size < 0:
        read_cnt = self._remain
      else:
        read_cnt = min(self._remain, size)
      data = self._stream.read(read_cnt)
      self._remain -= len(data)
    else:
      data = self._stream.read(size)
    if not data or self._check_size and not self._remain:
      self._eof = True
    return data

  def readline(self, size=-1):
    self._check_closed()
    if self._eof or size == 0: return ""
    if self._check_size:
      if size < 0:
        read_cnt = self._remain
      else:
        read_cnt = min(self._remain, size)
      line = self._stream.readline(read_cnt)
      self._remain -= len(line)
    else:
      line = self._stream.readline(size)
    if not line or self._check_size and not self._remain:
      self._eof = True
    return line

  def readlines(self, sizehint=0):
    self._check_closed()
    if self._eof: return []
    if self._check_size:
      lines = []
      remain = self._remain
      while remain:
        line = self._stream.readline(remain)
        lines.append(line)
        remain -= len(line)
    else:
      lines = self._stream.readlines()
    self._eof = True
    return lines

  def __iter__(self):
    return self

  def next(self):
    self._check_closed()
    line = self.readline()
    if not line:
      raise StopIteration
    return line

class IdentityOStream(object):

  name = "<IdentityOStream>"

  __slots__ = ("_stream", "_remain", "_check_size", "_eof", "_fileno")

  def __init__(self, stream, streamSize=-1):
    self._stream = stream
    self._fileno = self._stream.fileno()
    if streamSize < 0:
      self._remain = 0
      self._check_size = False
    else:
      self._remain = streamSize
      self._check_size = True

  closed = property(lambda self: self._stream is None)

  eof = property(lambda self: self._eof)

  def _check_closed(self):
    if self._stream is None:
      raise ValueError, "Stream is closed"

  def flush(self):
    self._stream.flush()

  def close(self):
    if self._stream is not None:
      try:
        self.flush()
      except:
        pass
      self._stream = None

  def __del__(self):
    self.close()

  def fileno(self):
    return self._fileno

  def write(self, data):
    self._check_closed()
    if not data:
      return
    if not isinstance(data, str):
      raise TypeError, "'data' must be string"
    self._writebytes(data)

  def writelines(self, sequence):
    self._check_closed()
    if not sequence:
      return
    if isinstance(sequence, str): # alone string is not allowed
      raise TypeError, "'sequence' must be sequence of strings"
    def check_type(param):
      if not isinstance(param, str):
        raise TypeError, "'sequence' must be sequence of strings"
    data = "".join(map(check_type, sequence))
    self._writebytes(data)

  def _writebytes(self, data):
    if self._check_size:
      if self._remain > 0:
        if self._remain < len(data):
          data = data[:self._remain]
          self._remain = 0
        else:
          self._remain -= len(data)
      else:
        return
    self._stream.write(data)

class ChunkedIStream(object):

  name = "<ChunkedIStream>"

  __slots__ = ("_stream", "_remain", "_eof", "_fileno")

  def __init__(self, stream):
    self._stream = stream
    self._fileno = self._stream.fileno()
    self._remain = 0
    self._eof = False

  closed = property(lambda self: self._stream is None)

  eof = property(lambda self: self._eof)

  def _check_closed(self):
    if self._stream is None:
      raise ValueError, "Stream is closed"

  def close(self):
    if self._stream is not None:
      self._stream = None

  def __del__(self):
    self.close()

  def fileno(self):
    return self._fileno

  def read(self, size=-1):
    self._check_closed()
    if self._eof or size == 0: return ""
    return self._readbytes(size)

  def readline(self, size=-1):
    self._check_closed()
    if self._eof or size == 0: return ""
    return self._readbytes(size, untilCRLF=True)

  def readlines(self, sizehint=0):
    self._check_closed()
    if self._eof: return []
    return self._readbytes().split()

  def _readbytes(self, size=-1, untilCRLF=False):
    buffers = []
    if untilCRLF:
      rfunc = self._stream.readline
    else:
      rfunc = self._stream.read
    if size > 0:
      sized = True
      read_left = size
    else:
      sized = False
    while True:
      if self._remain:
        if sized:
          rlen = min(self._remain, read_left)
        else:
          rlen = self._remain
        s = rfunc(rlen)
        self._remain -= len(s)
        if self._remain == 0:
          self._stream.read(2)
        if sized:
          read_left -= len(s)
        buffers.append(s)
        if untilCRLF and s[-1:] == '\n' or sized and read_left == 0:
          return ''.join(buffers)
      else:
        l = self._stream.readline()
        i = l.find(';')
        if i >= 0:
          l = l[:i] # strip chunk-extensions
        else:
          l = l[:-2]
        self._remain = int(l, 16)
        if self._remain == 0:
          while True: # ignore trailing headers
            l = self._stream.readline()
            if l == '\r\n':
              break
          self._eof = True
          return ''.join(buffers)

  def __iter__(self):
    return self

  def next(self):
    self._check_closed()
    line = self.readline()
    if not line:
      raise StopIteration
    return line

class ChunkedOStream(object):

  name = "<ChunkedOStream>"

  __slots__ = ("_stream", "_eof", "_fileno")

  def __init__(self, stream):
    self._stream = stream
    self._fileno = self._stream.fileno()
    self._eof = False

  closed = property(lambda self: self._stream is None)

  eof = property(lambda self: self._eof)

  def _check_closed(self):
    if self._stream is None:
      raise ValueError, "Stream is closed"

  def flush(self):
    self._stream.flush()

  def close(self):
    if self._stream is not None:
      try:
        self._stream.write("0\r\n\r\n")
        self.flush()
      except:
        pass
      self._stream = None

  def __del__(self):
    self.close()

  def fileno(self):
    return self._fileno

  def write(self, data):
    self._check_closed()
    if not data:
      return
    if not isinstance(data, str):
      raise TypeError, "'data' must be string"
    self._writebytes(data)

  def writelines(self, sequence):
    self._check_closed()
    if not sequence:
      return
    if isinstance(sequence, str): # alone string is not allowed
      raise TypeError, "'sequence' must be sequence of strings"
    def check_type(param):
      if not isinstance(param, str):
        raise TypeError, "'sequence' must be sequence of strings"
    data = "".join(map(check_type, sequence))
    self._writebytes(data)

  def _writebytes(self, data):
    self._stream.write("%X\r\n" % len(data))
    self._stream.write(data)
    self._stream.write("\r\n")
