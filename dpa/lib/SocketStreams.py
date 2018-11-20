import sys

class BaseSocketStream(object):

  defaultBufferSize = 16384
  name = "<BaseSocketStream>"

  __slots__ = ("_sock", "softspace", "_bufferSize", "_buf", "_eof", "_fileno")

  def __init__(self, sock, bufferSize=None):
    # bufferSize: -1 default Size
    #              0 unbuffered
    #              1 line buffered
    #             >1 actual buffer size
    self._sock = sock
    self._fileno = self._sock.fileno()
    self.softspace = False  # Must exists for file-like objects
    if bufferSize is None or bufferSize < 0:
      self._bufferSize = self.defaultBufferSize
    else:
      self._bufferSize = bufferSize
    self._buf = []
    self._eof = False

  closed = property(lambda self: self._sock is None)

  eof = property(lambda self: self._eof)

  def close(self):
    if self._sock is not None:
      try:
        self.flush()
      except:
        pass
      self._sock = None

  def __del__(self):
    self.close()

  def flush(self):
    pass

  def fileno(self):
    return self._fileno

  def _check_closed(self):
    if self._sock is None:
      raise ValueError, "Stream is closed"

class SocketIStream(BaseSocketStream):

  name = "<SocketIStream>"

  __slots__ = ("_recv", "_recv_size")

  def __init__(self, sock, bufferSize=None):
    super(SocketIStream, self).__init__(sock, bufferSize)
    self._recv = self._sock.recv
    if self._bufferSize == 0:
      self._recv_size = 1
    elif self._bufferSize == 1:
      self._recv_size = self.defaultBufferSize
    else:
      self._recv_size = self._bufferSize

  def read(self, size=-1):
    self._check_closed()
    if self._eof or size == 0: return ""
    if size < 0:
      if self._buf:
        buf = self._buf
        self._buf = []
      else:
        buf = []
      if self._bufferSize <= 1:
        recv_size = self.defaultBufferSize
      else:
        recv_size = self._bufferSize
      while True:
        data = self._recv(recv_size)
        if not data:
          self._eof = True
          break
        buf.append(data)
    else:
      if self._buf:
        data = self._buf[0]
        buf_len = len(data)
        if buf_len >= size:
          self._buf[0] = data[size:]
          return data[:size]
        else:
          buf = self._buf
          self._buf = []
      else:
        buf = []
        buf_len = 0
      while True:
        left = size - buf_len
        recv_size = max(self._recv_size, left)
        data = self._recv(recv_size)
        if not data:
          self._eof = True
          break
        buf.append(data)
        n = len(data)
        if n >= left:
          self._buf = [data[left:]]
          buf[-1] = data[:left]
          break
        buf_len += n
    return "".join(buf)

  def readline(self, size=-1):
    self._check_closed()
    if self._eof or size == 0: return ""
    if size < 0:
      check_size = False
    else:
      check_size = True
    if self._bufferSize <= 0: # Speed up unbuffered case
      buf = []
      buf_len = 0
      _recv = self._recv
      while True:
        data = _recv(1)
        if not data:
          self._eof = True
          break
        buf.append(data)
        buf_len += 1
        if data == "\n" or (check_size and buf_len >= size):
          break
      return "".join(buf)
    if self._buf:
      data = self._buf[0]
      if check_size:
        nl = data.find('\n', 0, size)
      else:
        nl = data.find('\n')
      if nl >= 0:
        nl += 1
        self._buf[0] = data[nl:]
        return data[:nl]
      if check_size:
        buf_len = len(data)
        if buf_len >= size:
          self._buf[0] = data[size:]
          return data[:size]
      buf = self._buf
      self._buf = []
    else:
      buf = []
      buf_len = 0
    while True:
      data = self._recv(self._bufferSize)
      if not data:
        self._eof = True
        break
      buf.append(data)
      if check_size:
        left = size - buf_len
        nl = data.find('\n', 0, left)
      else:
        nl = data.find('\n')
      if nl >= 0:
        nl += 1
        self._buf = [data[nl:]]
        buf[-1] = data[:nl]
        break
      if check_size:
        n = len(data)
        if n >= left:
          self._buf = [data[left:]]
          buf[-1] = data[:left]
          break
        buf_len += n
    return "".join(buf)

  def readlines(self, sizehint=0):
    self._check_closed()
    if self._eof: return []
    total = 0
    lineList = []
    while True:
      line = self.readline()
      if not line:
        break
      lineList.append(line)
      total += len(line)
      if sizehint and total >= sizehint:
        break
    return lineList

  def __iter__(self):
    return self

  def next(self):
    self._check_closed()
    line = self.readline()
    if not line:
      raise StopIteration
    return line

class SocketOStream(BaseSocketStream):

  name = "<SocketOStream>"

  __slots__ = ("_send", "_bufLen")

  def __init__(self, sock, bufferSize=None):
    super(SocketOStream, self).__init__(sock, bufferSize)
    self._send = self._sock.sendall
    self._bufLen = 0

  def flush(self):
    if self._buf:
      buf = "".join(self._buf)
      self._buf = []
      self._bufLen = 0
      self._send(buf)

  def write(self, data):
    self._check_closed()
    if not data:
      return
    if not isinstance(data, str):
      raise TypeError, "'data' must be string"
    self._buf.append(data)
    self._bufLen += len(data)
    if (self._bufferSize == 0 or
        self._bufferSize == 1 and '\n' in data or
        self._bufLen >= self._bufferSize):
      self.flush()

  def writelines(self, sequence):
    self._check_closed()
    if not sequence:
      return
    if isinstance(sequence, str): # alone string is not allowed
      raise TypeError, "'sequence' must be sequence of strings"
    def check_type(param):
      if not isinstance(param, str):
        raise TypeError, "'sequence' must be sequence of strings"
      self._bufLen += len(param)
      return param
    self._buf.extend(filter(None, map(check_type, sequence)))
    if (self._bufferSize <= 1 or
      self._bufLen >= self._bufferSize):
      self.flush()
