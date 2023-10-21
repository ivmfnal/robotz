from .core import PyThread, synchronized
import time, uuid, traceback
import sys

class Scheduler(PyThread):
    def __init__(self):
        PyThread.__init__(self)
        self.Tasks = {}     # id -> (function, t, interval, param, args)

    @synchronized        
    def add(self, fcn, interval=None, param=None, t0=None, id=None, **args):
        #
        # t0 - first time to run the task. Default:
        #   now + interval or now if interval is None
        # interval - interval to repeat the task. Default: do not repeat
        #
        # fcn:
        #   next_t = fcn()
        #   next_t = fcn(param)
        #   next_t = fcn(**args)
        # 
        #   next_t:
        #       "stop" - remove task
        #       int or float - next time to run
        #       None - run at now+interval next time
        #
        if id is None:
            id = uuid.uuid1().hex
        if t0 is None:
            t0 = time.time() + (interval or 0.0)
        self.Tasks[id] = (fcn, t0, interval, param, args)
        self.wakeup()
        return id
        
    @synchronized
    def remove(self, tid):
        if tid in self.Tasks:
            del self.Tasks[tid]
        
    @synchronized        
    def tick(self):
        #print("tick: tasks:", self.Tasks)
        
        now = time.time()
        tasks_to_run = []
        for tid, (fcn, t, interval, param, args) in list(self.Tasks.items()):
            if t <= now:
                with self.unlock:
                    next_t = None       # default
                    try:
                            if param is not None:
                                next_t = fcn(param)
                            elif args is not None:
                                next_t = fcn(**args)
                            else:
                                next_t = fcn()
                    except:
                        sys.stderr.write(traceback.format_exc())
                    #print("exiting unlock context...")
                #print("tick: next_t=", next_t)
                if tid in self.Tasks:
                    # the task may have been unregistered from within fcn() call
                    if next_t == "stop" or \
                            next_t is None and (interval is None or interval < 0.0):
                        del self.Tasks[tid]
                        continue
                    if next_t is None:
                        next_t = now + interval
                    #print("tick: next_t->", next_t)
                    self.Tasks[tid] = (fcn, next_t, interval, param, args)
                        
    def run(self):
        while True:
            delta = 10.0
            with self:
                if self.Tasks:
                    tmin = min(t for _, t, _, _, _ in self.Tasks.values())
                    now = time.time()
                    delta = tmin - time.time()
            if delta > 0.0:
                self.sleep(delta)
            self.tick()

if __name__ == "__main__":
    from datetime import datetime
    
    s = Scheduler()
    
    class NTimes(object):
        
        def __init__(self, n):
            self.N = n
            
        def __call__(self, message):
            t = datetime.now()
            print("%s: %s" % (strftime(t, "%H:%M:%S.f"), message))
            self.N -= 1
            if self.N <= 0:
                print("stopping", message)
                return "stop"
                
    s.start()
    time.sleep(1.0)
    s.add(NTimes(10), 1.5, "green 1.5 sec")
    s.add(NTimes(7), 0.5, "blue 0.5 sec")

    s.join()

        
