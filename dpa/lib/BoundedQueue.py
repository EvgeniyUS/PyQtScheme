import threading

class QueueTimeout(Exception): pass

class BoundedQueue:

  timeout = 0.5

  def __init__(self, limit=20):
    self.mon = threading.RLock()
    self.rc = threading.Condition(self.mon)
    self.wc = threading.Condition(self.mon)
    self.limit = limit
    self.queue = []

  def put(self, item):
    self.mon.acquire()
    while len(self.queue) >= self.limit:
      self.wc.wait()
    self.queue.append(item)
    self.rc.notify()
    self.mon.release()

  def get(self):
    self.mon.acquire()
    while not self.queue:
      self.rc.wait(self.timeout)
      if not self.queue:
        raise QueueTimeout
    item = self.queue.pop()
    self.wc.notify()
    self.mon.release()
    return item
