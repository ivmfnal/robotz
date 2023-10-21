from .core import Primitive, synchronized
from threading import current_thread
import threading

def _thread_id():
    return current_thread().ident

class RWLock(Primitive):
    
    def __init__(self):
        
        """
        Creates read-write lock. Read-write lock has 2 ways to ackquire it: *exclusive* and *shared*.
        If the read-write lock is already acquired in a shared way, it can be acquired by any number of threads in shared way
        without blocking, but an attempt to lock it exclusively will block until the lock is completely released.
        If the lock is acquired in exclusive way, any other attempt to lock it, in exclusive or shared way will block.
        
        The lock is reentrant in the sense that if a thread acquires it in exclusive mode, it can ackquire it again in exclusive mode.
        If the lock is scquired multiple times by a thread, it has to be released the same number of times.
        
        If the lock is acquired in the shared mode by only one thread, and the same thread is trying to acquire it in exclusive mode,
        the thread will not block, and the thread will be granted exclusive lock. When the thread later releases the exclusive lock,
        the lock still remains locked by the thread in shared mode until explicitly released.
        """
        
        Primitive.__init__(self)
        self.Exclusive = None
        self.ExclusiveCount = 0
        self.ExclusiveQueue = []
        self.Shared = {}
        
    def __purge(self):
        threads = set([t.ident for t in threading.enumerate()])
        if not self.Exclusive in threads:
            self.Exclusive = None
            self.ExclusiveCount = None
        for t in list(self.Shared.keys()):
            if not t in threads:
                del self.Shared[t]
        self.ExclusiveQueue = [t for t in self.ExclusiveQueue if t in threads]
    
    def __acq_exclusive(self):
        tid = _thread_id()
        self.__purge()
        if tid == self.Exclusive:
            self.ExclusiveCount += 1
            return True
        if self.Exclusive is None and (len(self.Shared) == 0 or len(self.Shared) == 1 and tid in self.Shared):
            if self.ExclusiveQueue:
                if tid == self.ExclusiveQueue[0]:
                    self.ExclusiveQueue = self.ExclusiveQueue[1:]
                else:
                    self.ExclusiveQueue.append(tid)
                    return False
            self.Exclusive = tid
            self.ExclusiveCount = 1
            return True
        return False
        
    def __rel_exclusive(self):
        tid = _thread_id()
        assert self.Exclusive == tid and self.ExclusiveCount > 0
        self.ExclusiveCount -= 1
        if self.ExclusiveCount <= 0:
            self.ExclusiveCount = 0
            self.Exclusive= None
        self.wakeup(all=True)
        
    def __acq_shared(self):
        tid = _thread_id()
        self.__purge()
        if not self.Exclusive in (None, tid):
            return False
        if not tid in self.Shared:
            self.Shared[tid] = 0
        self.Shared[tid] = self.Shared[tid] + 1
        return True
            
    def __rel_shared(self):
        tid = _thread_id()
        n = self.Shared.get(tid)
        assert n is not None and n > 0
        n -= 1
        if n == 0:
            del self.Shared[tid]
        else:
            self.Shared[tid] = n
        self.wakeup(all=True)
        
    @synchronized
    def acquireExclusive(self):
        while not self.__acq_exclusive():
            self.sleep()
            
    @synchronized
    def acquireShared(self):
        """
        Ackquires the lock in shared way. Will block if the lock is acquired by some other thread in exclusive mode.
        If the lock is exclusively locked by the same thread, the lock will also be locked in shared way and the method will return immediately.
        """
        while not self.__acq_shared():
            self.sleep()
            
    @synchronized
    def releaseExclusive(self):
        """
        Removes the exclusive lock if the calling thread holds it. If the lock was exclusively acquired multiple times by the thread,
        it will remain exclusively locked by the thread until it is exclusively-released the same number of times. 
        """
        self.__rel_exclusive()
        
    @synchronized
    def releaseShared(self):
        """
        Removes the shared lock if the calling thread holds it. If the lock was exclusively acquired multiple times by the thread,
        it will remain locked in shared mode by the thread until it is exclusively-released the same number of times. 
        """
        self.__rel_shared()

    @property
    def exclusive(self):
        """
        Create *context* object, which will acquire the lock in exclusive mode on entry and release it on exit
        For example:
        
            lock = RWLock()
        
            with lock.exclusive:
                # now the lock is exclusively locked
                ...
            # exit from the context removes the exclusive lock
        """
        
        class ExclusiveContext(object):
            def __init__(self, rwlock):
                self.RWLock = rwlock
            
            def __enter__(self):
                return self.RWLock.acquireExclusive()
            
            def __exit__(self, t, v, tb):
                return self.RWLock.releaseExclusive()
        return ExclusiveContext(self)
    
    @property
    def shared(self):
        """
        Create *context* object, which will acquire the lock in shared mode on entry and release it on exit
        For example:
        
            lock = RWLock()
        
            with lock.shared:
                # now the lock is locked in shared way
                ...
            # exit from the context removes the shared lock
        """
        class SharedContext(object):
            def __init__(self, rwlock):
                self.RWLock = rwlock
            
            def __enter__(self):
                return self.RWLock.acquireShared()
            
            def __exit__(self, t, v, tb):
                return self.RWLock.releaseShared()
            
        return SharedContext(self)
        
    @synchronized
    def owners(self):
        return self.Exclusive, list(self.Shared.keys())
        
