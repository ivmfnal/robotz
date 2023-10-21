from .core import PyThread, synchronized, Primitive, Timeout
from .task_queue import Task, TaskQueue
from .promise import Promise
import time, uuid, traceback, random
import sys

class Job(object):
    
    def __init__(self, scheduler, id, t, interval, jitter, fcn, count, params, args):
        self.F = fcn
        self.Params = params or ()
        self.Args = args or {}
        self.ID = id
        self.Interval = interval
        self.Jitter = jitter or 0.0
        self.NextT = t
        self.Scheduler = scheduler
        self.Count = count
        self.Promise = None
        
    def __str__(self):
        return f"Job({self.ID})"
        
    __repr__ = __str__
        
    def run(self):
        promise = self.Promise
        self.Promise = None
        self.Scheduler = None           # to break circular dependencies
        start = time.time()
        exc_info = None
        try:    
            #print(f"Job({self.ID}): running:", self.F, self.Params, self.Args)
            next_t = self.F(*self.Params, **self.Args)
            promise.complete()
        except Exception as e:
            #print(f"Job({self.ID}):", e)
            exc_info = sys.exc_info()
            #print(f"Job({self.ID}): exception:", traceback.format_exc())
            promise.exception(*exc_info)
            next_t = None
        else:
            #print(f"Job({self.ID}): done")
            pass
        if self.Count is not None:
            self.Count -= 1
            if self.Count <= 0:
                return None, exc_info
        if next_t == "stop":
            next_t = None
        elif next_t is None and self.Interval is not None:
            next_t = start + self.Interval + random.random() * self.Jitter
        if next_t is not None and next_t < 3.0e7:
            # if next_t is < 1980, it's relative time
            next_t = next_t + start + random.random() * self.Jitter
        return next_t, exc_info
        
    def cancel(self):
        """Cancels the job. If the job is currently running, it will not be stopped, but if it's a repeating job, calling this
        method will prevent the job from running again.
        """
        try: 
            self.Scheduler.remove(self)
        except: pass
        self.Scheduler = None

class JobThread(PyThread):
    
    def __init__(self, scheduler, job):
        PyThread.__init__(self, name=f"Scheduler({scheduler})/job{job.ID}", daemon=True)
        self.Scheduler = scheduler
        self.Job = job
        
    def run(self):
        scheduler = self.Scheduler
        job = self.Job
        self.Job = self.Scheduler = None
        next_t, exc_info = job.run()
        if exc_info:
            scheduler.job_failed(job, next_t, *exc_info)
        else:
            scheduler.job_ended(job, next_t)

class Scheduler(PyThread):
    def __init__(self, max_concurrent = 100, stop_when_empty = False, delegate=None, daemon=True, name=None, start=True, **args):
        """
        Args:
            max_concurrent (int): maximum number of concurrent jobs to run. Default: 100
            stop_when_empty (bool): stops the Scheduler thread when all the jobs complete. Default: False
            delegate (object): an object to notify when a job ends or fails
            daemon (bool): whether the Scheduler thread will run as daemon. Default: False
            name (str): name of the Scheduler
            start (bool): whether to start the Scheduler immediately on initialization. If False, the Scheduler needs to be started
                by calling ``start()`` method. Default: True
        """
        PyThread.__init__(self, daemon=daemon, name=name)
        self.Timeline = []      # [job, ...]
        self.Delegate = delegate
        self.StopWhenEmpty = stop_when_empty
        self.Stop = False
        if start:
            self.start()

    # delegate interface used to wait until the task queue is empty
    def job_ended(self, job, next_t):
        #print("job_ended:", job.ID)
        if self.Delegate is not None and hasattr(self.Delegate, "jobEnded"):
            try:    self.Delegate.jobEnded(self, task.JobID)
            except: pass
        if next_t is not None:
            self.add_job(job, next_t)
        self.wakeup()

    def job_failed(self, job, next_t, exc_type, exc_value, tb):
        #print("job_failed:", job.ID)
        if self.Delegate is not None and hasattr(self.Delegate, "jobFailed"):
            try:    self.Delegate.jobFailed(self, job.ID, exc_type, exc_value, tb)
            except: pass
        if next_t is not None:
            self.add_job(job, next_t)
        self.wakeup()
        
    @synchronized
    def jobs(self):
        return self.Timeline[:]

    def stop(self):
        """Stops the Scheduler thread"""
        self.Stop = True
        self.wakeup()
        
    @synchronized
    def add_job(self, job, t):
        job.NextT = t
        self.Timeline.append(job)
        job.Promise = promise = Promise(job).oncancel(job.cancel)
        self.wakeup()
        return promise
        
    @synchronized        
    def add(self, fcn, *params, interval=None, t=None, t0=None, id=None, jitter=0.0, param=None, count=None, **args):
        """Adds a new job to the schedule.
        
        Args:
            fcn (callable): will be called when the job starts
            params: positional arguments to pass to ``fcn``
            args: keyword arguments to to pass to ``fcn``
            interval (numeric): interval to repeat the job. Default: None (do not repeat)
            count (int): if ``interval`` is specified, specifies how many times to repeat the job. Default: unlimited
            t (numeric): pecifies the time when to fire the Timer first time. ``t`` can be either absolute timestamp - time in seconds since the
                Epoch or relative to current time. If ``t`` is less than 3e8 (~10 years), then it is interpreted as relative to current time.
                Default: current time plus ``interval``
            id (str): id to assign to the job. If None, the id will be generated automatically
            t0 - deprecated, alias to t, retained for backward compatibility
            param: deprecated, single positional parameter to pass to ``fcn``. Use ``params`` instead        
        
        Returns:
            Job: job object
        """
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
        if t is None: t = t0            # alias, t0 argument is deprecated
        if param is not None:       # for backward compatibility
            params = (param,)
        if id is None:
            id = uuid.uuid4().hex[:8]
        if t is None:
            t = time.time() + (interval or 0.0) + random.random()*jitter
        elif t < 10*365*24*3600:           # ~ Jan 1 1980
            t = time.time() + t
        job = Job(self, id, t, interval, jitter, fcn, count, params, args)
        return self.add_job(job, t)
        
    @synchronized
    def remove(self, job_or_id):
        """Removes the job from the schedule. Will not stop the job if it is already running.
        
        Args:
            job_or_id: Either the Job object returned by the ``add`` method, or job id (str)
        """
        job_id = job_or_id if isinstance(job_or_id, str) else job_or_id.ID
        self.Timeline = [j for j in self.Timeline if j.ID != job_id]

    @synchronized
    def run_jobs(self):
        keep_jobs = []
        next_run = None
        for job in self.Timeline:
            if job.NextT <= time.time():
                t = JobThread(self, job)
                t.start()
                self.wakeup()
            else:
                next_run = min(next_run or job.NextT, job.NextT)
                keep_jobs.append(job)
        self.Timeline = keep_jobs
        return next_run

    @synchronized
    def is_empty(self):
        """Returns True if there are no pending jobs on the schedule. Note that if a repeating job is currently running, it will not
        be on the schedule until it completes or fails.
        """
        return not self.Timeline
        
    
    @synchronized
    def _next_run(self):
        # returns run time of first job to run
        if self.Timeline:
            return min(j.NextT for j in self.Timeline)
        else:
            return None

    @synchronized
    def _job_is_ready(self):
        return any(j.NextT <= time.time() for j in self.Timeline)

    def run(self):
        while not self.Stop and not (self.is_empty() and self.StopWhenEmpty):
            with self:
                delta = 100
                if self.Timeline:
                    next_t = self.run_jobs()
                    if next_t is not None:
                        delta = next_t - time.time()
                self.sleep(delta)

    @synchronized        
    def wait_until_empty(self):
        """Wait until the schedule is empty. Note that if a repeating job is currently running, it will not
        be on the schedule until it completes or fails.
        """
        while not self.is_empty():
            self.sleep(10)
    
    join = wait_until_empty

_GLobalSchedulerLock = Primitive()
_GlobalScheduler = None

def global_scheduler(name="GlobalScheduler", **args):
    global _GlobalScheduler
    if _GlobalScheduler is None:
        with _GLobalSchedulerLock:
            if _GlobalScheduler is None:
                _GlobalScheduler = Scheduler(name=name, **args)
    return _GlobalScheduler

def schedule_job(fcn, *params, **args):
    return global_scheduler().add(fcn, *params, **args)

def unschedule_job(job_or_id):
    return global_scheduler().remove(job_or_id)

schedule_task = schedule_job        # aliases, deprecating term "job"
unschedule_task = unschedule_job

if __name__ == "__main__":
    from datetime import datetime
    
    s = Scheduler()
    
    class NTimes(object):

        def __init__(self, n):
            self.LastRun = None
            self.N = n

        def __call__(self, message):
            t = datetime.now()
            delta = None if self.LastRun is None else t - self.LastRun
            print("%s: %s delta:%s" % (t.strftime("%H:%M:%S.%f"), message, delta))
            self.LastRun = t
            self.N -= 1
            time.sleep(0.2)
            if self.N <= 0:
                print("stopping", message)
                return "stop"

    #time.sleep(1.0)
    s.add(NTimes(10), "green 1.5 sec", interval=1.5)
    s.add(NTimes(7), "blue 0.5 sec", interval=0.5)
    s.start()

    print("waiting for the scheduler to finish...")
    #s.join()
    s.wait_until_empty()
    s.stop()
    s.join()
    print("stopped")
