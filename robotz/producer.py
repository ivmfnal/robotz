from .core import Robot
from .dequeue import DEQueue

class Producer(Robot):
    
    def __init__(self, capacity=None, name=None):
        Robot.__init__(self, name=name)
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

