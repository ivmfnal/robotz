from .core import Primitive, synchronized
from .promise import Promise
from .dequeue import DEQueue
from .task_queue import Task, TaskQueue

class Gate(Primitive):

    def __init__(self, open=False):
        Primitive.__init__(self)
        self.Queue = []
        self.Open = open
        
    def wait(self, timeout=None):
        with self:
            if self.Open:   return
            promise = Promise()
            self.Queue.append(promise)
        return promise.wait(timeout=timeout)
        
    @synchronized
    def open(self, message=None):
        self.Open = True
        for p in self.Queue:
            p.complete(message)
        self.Queue = []

    @synchronized
    def close(self):
        self.Open = False
        
    @synchronized
    def pulse(self, message=None, limit=None):
        #
        # unblocks first or last "limit" blocked processes keeping the gate closed
        # if limit is None, unblocks all waiting processes
        # if limit > 0, unblocks first "limit" processes
        # if limit < 0, unblocks last "limit" processes
        #
        if limit is None:
            to_release = self.Queue
            self.Queue = []
        elif limit < 0:
            to_release = self.Queue[limit:]
            self.Queue = self.Queue[:limit]
        else:
            to_release = self.Queue[:limit]
            self.Queue = self.Queue[limit:]
        for p in to_release:
            p.complete(message)

            
            
        
    
        
        
        