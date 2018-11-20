#  SharedLock.py based on ASPN recipe http://code.activestate.com/recipes/502283/
#  Copyright (c) 2008 Mike D. Rozhnov
#
#  Original copyright:
# Copyright (C) 2007, Heiko Wundram. Released under the BSD-license.

from threading import Condition, Lock, currentThread
from time import time


class SharedLockError(Exception): pass

class SharedLockTimeoutError(SharedLockError): pass


class SharedLock(object):

  def __init__(self):
    self.__condition = Condition(Lock())
    self.__writer = None
    self.__writerCount = 0
    self.__upgradeWriterCount = 0
    self.__pendingWriters = []
    self.__readers = {}

  def acquireRead(self, timeout=None):
    if timeout is not None:
      endtime = time() + timeout
    me = currentThread()
    self.__condition.acquire()
    try:
      if self.__writer is me:
        # If we are the writer, grant a new read lock, always.
        self.__writerCount += 1
        return
      while True:
        if self.__writer is None:
          # Only test anything if there is no current writer.
          if self.__upgradeWriterCount or self.__pendingWriters:
            if me in self.__readers:
              # Only grant a read lock if we already have one
              # in case writers are waiting for their turn.
              # This means that writers can't easily get starved
              # (but see below, readers can).
              self.__readers[me] += 1
              return
          # No, we aren't a reader (yet), wait for our turn.
          else:
            # Grant a new read lock, always, in case there are
            # no pending writers (and no writer).
            self.__readers[me] = self.__readers.get(me, 0) + 1
            return
        if timeout is not None:
          remaining = endtime - time()
          if remaining <= 0:
            # Timeout has expired, signal caller of this.
            raise SharedLockTimeoutError, "Timeout during read lock acquisition"
          self.__condition.wait(remaining)
        else:
          self.__condition.wait()
    finally:
      self.__condition.release()

  def acquireWrite(self, timeout=None):
    if timeout is not None:
      endtime = time() + timeout
    me = currentThread()
    upgradeWriter = False
    self.__condition.acquire()
    try:
      if self.__writer is me:
        self.__writerCount += 1
        return
      elif me in self.__readers:
        # If we are a reader, no need to add us to pendingwriters,
        # we get the upgradeWriter slot.
        if self.__upgradeWriterCount:
          # If we are a reader and want to upgrade, and someone
          # else also wants to upgrade, there is no way we can do
          # this except if one of us releases all his read locks.
          # Signal this to user.
          raise SharedLockError, "Dead lock attempt, denying write lock"
        upgradeWriter = True
        self.__upgradeWriterCount = self.__readers.pop(me)
      else:
        # We aren't a reader, so add us to the pending writers queue
        # for synchronization with the readers.
        self.__pendingWriters.append(me)
      while True:
        if not self.__readers and self.__writer is None:
          # Only test anything if there are no readers and writers.
          if self.__upgradeWriterCount:
            if upgradeWriter:
              # There is a writer to upgrade, and it's us. Take
              # the write lock.
              self.__writer = me
              self.__writerCount = self.__upgradeWriterCount + 1
              self.__upgradeWriterCount = 0
              return
          # There is a writer to upgrade, but it's not us.
          # Always leave the upgrade writer the advance slot,
          # because he presumes he'll get a write lock directly
          # from a previously held read lock.
          elif self.__pendingWriters[0] is me:
            # If there are no readers and writers, it's always
            # fine for us to take the writer slot, removing us
            # from the pending writers queue.
            # This might mean starvation for readers, though.
            self.__writer = me
            self.__writerCount = 1
            self.__pendingWriters = self.__pendingWriters[1:]
            return
        if timeout is not None:
          remaining = endtime - time()
          if remaining <= 0:
            # Timeout has expired, signal caller of this.
            if upgradeWriter:
              # Put us back on the reader queue. No need to
              # signal anyone of this change, because no other
              # writer could've taken our spot before we got
              # here (because of remaining readers), as the test
              # for proper conditions is at the start of the
              # loop, not at the end.
              self.__readers[me] = self.__upgradeWriterCount
              self.__upgradeWriterCount = 0
            else:
              # We were a simple pending writer, just remove us
              # from the FIFO list.
              self.__pendingWriters.remove(me)
            raise SharedLockTimeoutError, "Timeout during write lock acquisition"
          self.__condition.wait(remaining)
        else:
          self.__condition.wait()
    finally:
      self.__condition.release()

  def release(self):
    me = currentThread()
    self.__condition.acquire()
    try:
      if self.__writer is me:
        self.__writerCount -= 1
        if not self.__writerCount:
          # No more write locks; take our writer position away and
          # notify waiters of the new circumstances.
          self.__writer = None
          self.__condition.notifyAll()
      elif me in self.__readers:
        # We are a reader currently, take one nesting depth away.
        self.__readers[me] -= 1
        if not self.__readers[me]:
          # No more read locks, take our reader position away.
          del self.__readers[me]
          if not self.__readers:
            # No more readers, notify waiters of the new
            # circumstances.
            self.__condition.notifyAll()
      else:
        raise SharedLockError, "Attempt to release unheld lock"
    finally:
      self.__condition.release()
