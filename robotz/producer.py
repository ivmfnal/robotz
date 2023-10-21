from .core import PyThread
from .dequeue import DEQueue

class Producer(PyThread):
    
    def __init__(self, capacity=None, name=None):
        PyThread.__init__(self, name=name)
        self.OutQueue = DEQueue(capacity=capacity)
    
    def __iter__(self):
        try:    self.start()
        except RuntimeError:
            pass    # already started: ignore
        for item in self.OutQueue:
            yield item
            
    def emit(self, item):
        self.OutQueue.append(item)
        
    def close(self):
        self.OutQueue.close()

