import time, traceback, sys
from .core import Primitive, PyThread, synchronized
from .dequeue import DEQueue
from threading import RLock

class Task(Primitive):

    def __init__(self):
        Primitive.__init__(self)
        self._t_Started = None
        self._t_Ended = None
    
    #def __call__(self):
    #    pass

    def run(self):
        raise NotImplementedError
        
    @synchronized
    @property
    def started(self):
        return self._t_Started is not None
        
    @synchronized
    @property
    def running(self):
        return self._t_Started is not None and self._t_Ended is None
        
    @synchronized
    @property
    def ended(self):
        return self._t_Started is not None and self._t_Ended is not None
        
class FunctionTask(Task):

    def __init__(self, fcn, *params, **args):
        Task.__init__(self)
        self.F = fcn
        self.Params = params
        self.Args = args
        
    def run(self):
        return self.F(*self.Params, **self.Args)
        
class _Worker(PyThread):
    
    def __init__(self, queue):
        PyThread.__init__(self)
        self.Queue = queue
        
    def run(self):
        while not self.Queue.ShutDown:
            task = self.Queue.nextTask()
            if task is None:
                break
            exc_type, value, tb = None, None, None
            self.Queue.taskStarted(task)            
            try:
                if callable(task):
                    task()
                else:
                    task._t_Started = time.time()
                    task.run()
            except:
                exc_type, value, tb = sys.exc_info()
            finally:
                if not callable(task):
                    task._t_Ended = time.time()
                self.Queue.taskEnded(task, exc_type, value, tb)
        
class TaskQueue(Primitive):
    
    def __init__(self, nworkers, capacity=None, stagger=None, delegate=None, tasks=[]):
        Primitive.__init__(self)
        self.NWorkers = nworkers
        self.Running = []
        self.Queue = DEQueue(capacity)
        self.Closed = False
        self.Stagger = stagger or 0.0
        self.LastStart = 0.0
        self.Delegate = delegate
        self.ShutDown = False
        self.GetLock = RLock()
        self.Held = False
        self.Workers = [_Worker(self) for _ in range(nworkers)]
        for t in tasks:
            self.addTask(t)
        for w in self.Workers:
            w.daemon = True
            w.start()
        

    def addTask(self, task, timeout = None):
        if self.Closed:
            raise RunTimeError("Queue closed")
        self.Queue.append(task, timeout=timeout)
        self.wakeup(all=False)
        return self
        
    append = addTask

    def __iadd__(self, task):
        return self.addTask(task)
        
    def __lshift__(self, task):
        return self.addTask(task)
        
    def insertTask(self, task, timeout = None):
        if self.Closed:
            raise RunTimeError("Queue closed")
        self.Queue.insert(task, timeout=timeout)
        self.wakeup(all=False)
        return self
        
    insert = insertTask
        
    def __rrshift__(self, task):
        return self.insertTask(task)
        
    def close(self):
        self.Closed = True
        self.Queue.close()
        self.wakeup()
        
    def hold(self):
        self.Held = True
        
    def release(self):
        self.Held = False
        self.wakeup()
        
    def nextTask(self):
        if self.Closed:
            return None
        with self.GetLock:
            if self.Stagger:
                now = time.time()
                tnext = self.LastStart + self.Stagger
                if now < tnext:
                    time.sleep(tnext - now)
            while (self.Held or self.Queue.empty()) and not self.Closed:
                self.sleep()
            if self.Closed:
                return None
            task = self.Queue.pop()
            if task is not None:
                self.Running.append(task)
            self.LastStart = time.time()
            self.wakeup()
            return task
        
    def taskStarted(self, task):
        if self.Delegate is not None:
            self.Delegate.taskStarted(self, task)
        
    def taskEnded(self, task, exc_type, exc_value, tb):
        with self:
            while task in self.Running:
                self.Running.remove(task)

        self.wakeup()
        if exc_type is not None:
            if self.Delegate is None:
                sys.stdout.write("Exception in task %s:\n" % (task, ))
                traceback.print_exception(exc_type, exc_value, tb, file=sys.stderr)
            else:
                try:
                    self.Delegate.taskFailed(self, task,  exc_type, exc_value, tb)
                except:
                    traceback.print_exc(file=sys.stderr)
        else:
            if self.Delegate is not None:
                self.Delegate.taskEnded(self, task)
                
    def nrunning(self):
        return len(self.Running)
        
    def counts(self):
        return len(self.Queue), len(self.Running)
        
    def flush(self):
        self.Queue.flush()
        
    @synchronized
    def tasks(self):
        return self.Queue.items(), self.Running[:]
            
    @synchronized
    def activeTasks(self):
        return self.Running[:]
        
    @synchronized
    def waitingTasks(self):
        return self.Queue.items()
 
    @synchronized
    def isEmpty(self):
        empty = len(self.Queue) == 0 and not self.Running
        return empty
                
    @synchronized
    def waitUntilEmpty(self):
        # wait until all tasks are done and the queue is empty
        while not self.isEmpty():
            self.sleep()

                
    join = waitUntilEmpty
                
    def __len__(self):
        return len(self.Queue)
        
    def destroy(self):
        self.ShutDown = True
        self.Workers = None

if __name__ == '__main__':
    
    class T(Task):
        
        def __init__(self, i):
            Task.__init__(self)
            self.I = i
        
        def run(self):
            time.sleep(0.15)
            print("Task", self.I)
    
    q = TaskQueue(3, capacity=5, stagger=0.1)
    for _ in range(100):
        q << T()
