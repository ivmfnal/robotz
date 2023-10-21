from .core import Primitive, synchronized
import time

class DEQueue(Primitive):

    def __init__(self, capacity=None):
        Primitive.__init__(self)
        self.Capacity = capacity
        self.List = []
        self.Closed = False
    
    @synchronized
    def close(self):
        self.Closed = True
        self.wakeup()

    @synchronized
    def open(self):
        self.Closed = False
        self.wakeup()

    def _wait_for_room(self, timeout):
        # must be called from a synchronized method !
        t0 = time.time()
        t1 = None if timeout is None else t0 + timeout
        while self.Capacity is not None and len(self.List) >= self.Capacity \
                        and not self.Closed:
            dt = None
            if t1 is not None:
                t = time.time()
                if t > t1:
                    raise RuntimeError("Operation timed-out")
                dt = t1 - t
            self.sleep(dt)

    @synchronized    
    def append(self, item, timeout=None, force=False):
        if not force:
            self._wait_for_room(timeout)
        if self.Closed:
            raise RuntimeError("Queue is closed")
        self.List.append(item)
        self.wakeup()
        
    def __lshift__(self, item):
        return self.append(item)
    
    put = append
    
    @synchronized    
    def insert(self, item, timeout=None, force=False):
        if not force:
            self._wait_for_room(timeout)
        if self.Closed:
            raise RuntimeError("Queue is closed")
        self.List.insert(0, item)
        self.wakeup()

    def __rrshift__(self, item):
        return self.insert(item)

    @synchronized
    def pop(self, index=0, timeout=None):
        while not (self.List or self.Closed):
            self.sleep(timeout)
        try:    
            item = self.List.pop(index)
            self.wakeup()       # in case someone is waiting to add an item
        except IndexError:
            item = None         # closed
        return item

    get = pop

    #
    # Iterator protocol
    # 
    # for item in queue:        # wait for next item to arrive
    #   # ... process item
    #
    
    def __iter__(self):
        return self

    def __next__(self):
        item = self.pop()
        if item is None:
            raise StopIteration()
        else:
            return item
        raise StopIteration()

    next = __next__
        
    @synchronized
    def flush(self):
        self.List = []
        self.wakeup()
        
    @synchronized
    def items(self):
        return self.List[:]
        
    @synchronized
    def look(self):
        return self.List[0] if self.List else None
        
    @synchronized
    def popIfFirst(self, x):
        if self.List:
            first = self.List[0]
            if first is x or first == x:
                self.pop()
                return x
        return None

    def empty(self):
        return not self.List
        
    def __len__(self):
        return len(self.List)
    
    def __contains__(self, item):
        return item in self.List
        
    def remove(self, item):
        self.List.remove(item)
        self.wakeup()
