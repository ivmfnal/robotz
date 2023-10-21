from .task_queue import TaskQueue, Task
from .core import Primitive, synchronized

class Gang(Primitive):

    def __init__(self, callable, params=None, n=1, concurrency=None, stagger=None, delegate=None):
        self.Queue = TaskQueue(concurrency, stagger=stagger, delegate=delegate or self)
        if params is None:
            params = [None] * n
        self.Promises = [self.Queue.add(callable, param).promise for param in params]

    def __iter__(self):
        return (promise.wait() for promise in self.Promises)

    def wait(self):
        return list(self.__iter__())
