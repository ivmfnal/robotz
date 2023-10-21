from threading import RLock, Thread, Event, Condition, Semaphore, currentThread, get_ident
import time
import sys

Waiting = []
In = []

class Timeout(Exception):
    pass

class QueueClosed(Exception):
    pass

def threadName():
    t = currentThread()
    return str(t)

def synchronized(method):
    def smethod(self, *params, **args):
        me = get_ident()
        with self:
            out = method(self, *params, **args)
        return out
    smethod.__doc__ = method.__doc__
    return smethod

def gated(method):
    def smethod(self, *params, **args):
        with self._Gate:
            out = method(self, *params, **args)
        return out
    smethod.__doc__ = method.__doc__
    return smethod


def printWaiting():
    print("waiting:----")
    for w in Waiting:
        print(w)
    print("in:---------")
    for w in In:
        print(w)

class UnlockContext(object):
    
    def __init__(self, prim):
        self.Prim = prim
        
    def __enter__(self):
        self.Prim._Lock.__exit__(None, None, None)
        
    def __exit__(self, exc_type, exc_value, traceback):
        self.Prim._Lock.__enter__()    

class Primitive:
    def __init__(self, gate=1, lock=None, name=None):
        """
        Initiaslizes new Primitive object
        
        Args:
            gate (int): initial value for the Gate semapthore. Default = 1
            lock (Lock or RLock): Lock or RLock for the primitive to use. Default - new RLock object
            name (str): Name for the primitive. Default - unnamed
        """
        self._Kind = self.__class__.__name__
        self._Lock = lock if lock is not None else RLock()
        #print ("Primitive:", self, " _Lock:", self._Lock)
        self._WakeUp = Condition(self._Lock)
        self._Gate = Semaphore(gate)
        self.Name = name
        self.Timer = None
        
    def __str__(self):
        ident = ('"%s"' % (self.Name,)) if self.Name else ("@%s" % (("%x" % (id(self),))[-4:],))
        return "[%s %s]" % (self._Kind, ident)

    def __get_kind(self):
        return self._Kind

    def __set_kind(self, kind):
        self._Kind = kind

    kind = property(__get_kind, __set_kind)

    def getLock(self):
        """Returns the primitive's lock object. It can be used to create Primitives using the same lock object.
        
        Returns:
            Lock or RLock: primitive's lock object
        """
        return self._Lock
        
    def __enter__(self):
        """Primitive's context entry. Using a primitve as a context is equivalent to using its
        lock as the context. The following are equivalent:
        
            with my_primitive:
                ...
        
            with my_primitive.getLock():
                ...
        """
        return self._Lock.__enter__()
        
    def __exit__(self, exc_type, exc_value, traceback):
        """Primitive's context exit
        """
        return self._Lock.__exit__(exc_type, exc_value, traceback)

    def can_lock(self):
        """Returns True if the thread can lock the Primitive's lock immediately, False otherwise.
        Does not guarantee that a subsequent attempt to lock the Primitive will succeed immediately.
        """
        if self._Lock.acquire(blocking=False):
            self._Lock.release()
            return True
        else:
            return False

    @property
    def unlock(self):
        """Creates a context which can be used to temporarily release the lock acquired on the
        primitive eariler. For example:
        
            with my_primitive:
                # do something, which needs to be done while the primitive is locked
                with my_primitive.unlock:
                    # temporarily unlock the primitive and do something else
                # re-acquire the primitive's lock again, possibly waiting for it
                # continue doing something while the primitive is locked again
        """
        return UnlockContext(self)

    @synchronized
    def sleep(self, timeout = None, function=None, arguments=()):
        """
        Blocks until wakep() method is called on the same primitive. The primitive will be unlocked for the duration of the sleep() call.
        Then the primitive will be locked again and if the function is provided, it will be called while the primitive is locked
        and then the sleep() methot will unlock the primitive and return the result.
        
        Args:
            timeout (float or int): time-out. If timed-out, RuntimeError exception will be raised.
        """
        self._WakeUp.wait(timeout)
        if function is not None:
            result = function(*arguments)
            return result

    @synchronized
    def sleep_until(self, predicate, *params, timeout = None, **args):
        """
        Blocks until a condition is satisfied. The method will continue calling sleep() and when it wakes up, it will call the
        predicate function and check if the predicate is satisfied and if not go back to sleep. The predicate function is
        expected to return True or False. Basically, sleep_until implements this loop inside a critical section.
        Note that the primitive is unlocked while the sleep() is in progress.
        
            with self:
                while not timed-out:
                    primitive.sleep()
                    if predicate(*params, **args):
                        break

        Args:
            predicate (function): a function returning True or False. The method will exit when the function returns True
            params: positional arguments to pass to each predicate function call
            args: keyword arguments to pass to each predicate function call
            timeout (int or float): timeout. If timed-out, RuntimeError exception will be raised
        """
        #print("sleep", self, get_ident(), "   condition lock:", self._WakeUp._lock, "...")
        t1 = None if timeout is None else time.time() + timeout
        while (t1 is None or time.time() < t1):
            if predicate(*params, **args):
                return
            delta = None
            if t1 is not None:
                delta = max(0.0, t1 - time.time())
            self.sleep(delta)
        else:
            raise Timeout()
            
    @synchronized
    def wakeup(self, n=1, all=True, function=None, arguments=()):
        """Wakes up all or some thread, which is sleeping on the primitive.
        
        Args:
            n (int): number of threads to wake up. Default is 1
            all (bool): wake up all threads sleeping on the primitive. If True, ``n`` argument is ignored
        """
        
        if function is not None:
            function(*arguments)
        if all:
            self._WakeUp.notifyAll()
        else:
            self._WakeUp.notify(n)
            
    @synchronized
    def alarm(self, *params, **args):
        """Starts a new "alarm" Timer thread associated with the Primitive. A Primitive can have only one alarm thread associated with it.
        If another alarm thread was already created using a previous call to alarm(), the old thread will be cancelled and
        deleted.
        
        Args:
            params: positional arguments to pass to the Timer constructor
            args: keyword arguments to pass to the Timer constructor
        """
        self.cancel_alarm()
        self.Timer = Timer(*params, **args)

    @synchronized
    def cancel_alarm(self):
        """
        Cancels the alarm thread associated with the Primitive, if any. 
        """
        
        if self.Timer is not None:
            self.Timer.cancel()
            self.Timer = None

class PyThread(Thread, Primitive):
    def __init__(self, *params, name=None, **args):
        """Initializes a new PyThread object. PyThread is a subclass of both threading.Thread and Primitive, so it combines features of both.
        
        Args:
            name (string):  Name for the Primitive
            params: positional arguments for threading.Thread constructor
            args: keyword arguments for threading.Thread constructor
        """
        Thread.__init__(self, *params, **args)
        Primitive.__init__(self, name=name)
        self.Stop = False
        
    def stop(self):
        self.Stop = True

class Timer(PyThread):
    
    def __init__(self, fcn, *params, t=None, interval=None, start=True, name=None, daemon=True, onexception=None, **args):
        """Initializes new Timer thread. pythreader's Timer is similar in functionality with threading.Timer, but it has additional
        functionality. In particular pythreader's Timer can run as a periodic timer, firing at specified frequency until it is cancelled.
        
        Args:
            fcn (function): function to call every time the Timer fires
            params: positional arguments to pass to the ``fcn``
            args: keyword arguments to pass to the ``fcn``
            t (numeric): specifies the time when to fire the Timer first time. ``t`` can be either absolute timestamp - time in seconds since the
                Epoch or relative to current time. If ``t`` is less than 3e8 (~10 years), then it is interpreted as relative to current time.
                Default: current time plus ``interval``
            start (bool): to start the Timer thread immediately. Otherwise, the Timer thread will be created but not run until started explicitly
                using ``start()`` method. Default: start immediately
            daemon (bool): whether the Timer thread should be a daemon thread. Default: True
            onexception (function): a callback to call if ``fcn`` raies an exception. The callback will be called with 3 arguments:
                exception type, exception value and the traceback, similar to what sys.exc_info() returns. Default: ignore any exceptions raised by ``fcn``
        """
        
        PyThread.__init__(self, name=name, daemon=daemon)
        if t is None:
            self.T = time.time() + interval
        else:
            self.T = t if t > 3e8 else time.time() + t
        self.Fcn = fcn
        self.OnException = onexception
        self.Params = params
        self.Args = args
        self.Interval = interval
        self.Cancelled = False
        self.Paused = False
        if start:
            self.start()

    def run(self):
        try:
            again = True
            while again and not self.Cancelled:
                again = False
                now = time.time()
                if now < self.T:
                    self.sleep(self.T - now)
                while self.Paused and not self.Cancelled:
                    self.sleep(100)
                if not self.Cancelled:
                    try:    self.Fcn(*self.Params, **self.Args)
                    except:
                        if self.OnException is not None:
                            try:
                                self.OnException(*sys.exc_info())
                            except:
                                pass
                    if not self.Cancelled and self.Interval:
                        self.T = time.time() + self.Interval
                        again = True
        finally:
            # to break any circular links
            self.Fcn = self.Args = self.Params = None

    def cancel(self):
        """Cancels the Timer thread
        """
        self.Cancelled = True
        self.wakeup()

    def pause(self):
        """Pauses the Timer thread. In fact the thread will continue running, but it will not fire intil ``resume`` method is called
        """
        self.Paused = True

    def resume(self):
        """Resumes the timer firing. Next time the timer will not necessarily fire immediately when resumed, but it will fire at the next
        end of the firing interval.
        """
        self.Paused = False
        self.wakeup()


