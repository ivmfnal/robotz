from .core import Primitive, synchronized
from .promise import Promise

class Barrier(Primitive):

    def __init__(self, height):
        Primitive.__init__(self)
        self.Queue = []
        self.Height = height
        
    def wait(self, timeout=None):
        with self:
            if len(self.Queue) >= self.Height - 1:
                self.flush()
                return
            else:
                promise = Promise()
                self.Queue.append(promise)
        promise.wait(timeout=timeout)
        
    @synchronized
    def flush(self):
        for p in self.Queue:
            p.complete()
        self.Queue = []
        
