from .core import Primitive, synchronized, Timeout
from threading import get_ident, RLock

class DebugLock(object):
    
    def __init__(self):
        self.R = RLock()
        
    def acquire(self, *params, **args):
        print(self, "acquire by ", get_ident(), "...")
        self.R.acquire(*params, **args)
        print(self, "acquired by ", get_ident())
        
    def release(self):
        print(self, "released by ", get_ident())
        self.R.release()
        
    def __enter__(self):
        return self.acquire()
        
    def __exit__(self, *params):
        return self.release()
    

class Promise(Primitive):
    
    def __init__(self, data=None, callbacks = [], name=None):
        """
        Creates new Promise object.
        
        Args:
            data: Arbitrary user-defined data to be associated with the promise. Can be anything. pythreader does not use it.
            callbacks (list): List of Promise callbacks objects. Each object may have ``oncomplete`` and/or ``onexception`` methods defined. See Notes below.
            name (string): Name for the new Promise object, optional.
        
        Notes:
            
        """
        Primitive.__init__(self, name=name)    #, lock=DebugLock())
        self.Data = data
        self.Callbacks = callbacks[:]
        self.Complete = False
        self.Cancelled = False
        self.Result = None
        self.ExceptionInfo = None     # or tuple (exc_type, exc_value, exc_traceback)
        self.RaiseException = True
        self.OnComplete = self.OnException = self.OnCancel = None
        self.Chained = []

    @synchronized
    def then(self, oncomplete=None, onexception=None):
        """
        Creates new Promise object, which will be chained to the ``self`` promise with provided ``oncomplete`` and/or ``onexception`` callbacks.
        
        Args:
            oncomplete (function): the new promise completion callback function
            oncexception (function): the new promise exception callback function
        """
        p = Promise()
        if oncomplete is not None:
            p.oncomplete(oncomplete)
        if onexception is not None:
            p.onexception(onexception)
        self.chain(p)
        return p

    @synchronized
    def oncomplete(self, cb):
        """Sets promise completion callback. If the promise has already completed, the callback function is called immediately.
        Old completion callback is removed.

        Args:
            cb (function):    Function to be called when the promise completes. The function will be called with the following arguments:

                cb(promise, result)
        """
        if self.Complete:
            cb(self, self.Result)
        self.OnComplete = cb
        return self
        
    @synchronized
    def onexception(self, cb):
        """Sets promise exception callback. If the promise has failed already, the callback function will be called immediately.
        Old exception callback is removed.
        
        Args:
            cb (function):    Function to be called when the promise fails. The function will be called with the following arguments:
        
                cb(promise, exception_type, exception_value, traceback)
        """
        if self.ExceptionInfo:
            cb(self, *self.ExceptionInfo)
        self.OnException = cb
        return self
        
    @synchronized
    def oncancel(self, cb):
        """Sets promise cancellation callback. If the promise has been cancelled already, the callback function will be called immediately.
        Old cancellation callback is removed.
        
        Args:
            cb (function):    Function to be called when the promise is cancelled. The function will be called with the promise as the only
                argiment.
        """
        if self.Cancelled:
            cb(self)
        self.OnCancel = cb
        return self
        
    @synchronized
    def addCallback(self, cb):
        """Adds a new promise callback object to the promise callback list. If the promise has completed, failed or cancelled already,
            the new callback object will be notified immediately and will not be added to the list.
        
        Args:
            cb (object):    New Promise callback object. The callback object is expected to have some (or none) of the following methods:
        
                def oncancel(self, promise):
                    # the promise was cancelled

                def oncomplete(self, promise, result):
                    # the promise completed

                def onexception(self, promise, exception_type, exception_value, traceback):
                    # the promise failed        
        """
        if self.Cancelled and hasattr(cb, "oncancel"):
            cb.oncancel(self)
        elif self.Complete and hasattr(cb, "oncomplete"):
            cb.oncomplete(self, self.Result)
        elif self.ExceptionInfo and hasattr(cb, "onexception"):
            cb.onexception(self, *self.ExceptionInfo)
        else:
            self.Callbacks.append(cb)
        return self

    @synchronized
    def chain(self, *promises, cancel_chained = True):
        """Adds new chained promises to ``self``. If the ``self`` promise has delivered (completed or failed) already, the new
        promises will be delivered with the same status immediately. If the ``self`` promise has been cancelled, the new promises will be cancelled too.
        
        Args:
            promises (list of Promises): list of promises to add as chained
            cancel_chained (bool): whether to cancel the new promises if the ``self`` promise has been cancelled. Default = True
        """
        if self.ExceptionInfo:
            exc_type, exc_value, exc_traceback = self.ExceptionInfo
            for p in promises:
                p.exception(exc_type, exc_value, exc_traceback)
        elif self.Complete:
            for p in promises:
                p.complete(self.Result)
        elif self.Cancelled and cancel_chained:
            for p in promises:
                p.cancel()
        else:
            self.Chained += list(promises)
        return self

    @synchronized
    def complete(self, result=None):
        """Delivers the promise as successfully completed with given result
            
            Args:
                result: the promise result to be delivered
        """
        self.Result = result
        self.Complete = True
        if not self.Cancelled:
            stop = False
            if self.OnComplete is not None:
                stop = not not self.OnComplete(self, self.Result)
            for cb in self.Callbacks:
                if stop:
                    break
                if hasattr(cb, "oncomplete"):
                    stop = not not cb.oncomplete(self.Result, self)
        for p in self.Chained:
            p.complete(result)
        self.wakeup()
        self._cleanup()

    @synchronized
    def exception(self, exc_type, exc_value, exc_traceback):
        """Fails the promise with the exception
            
            Args:
                exc_type: exception type
                exc_value: exception value
                exc_traceback: exception traceback
        """
        self.ExceptionInfo = (exc_type, exc_value, exc_traceback)
        if not self.Cancelled:
            stop = False
            if self.OnException is not None:
                stop = bool(self.OnException(self, exc_type, exc_value, exc_traceback))
            for cb in self.Callbacks:
                if stop:
                    break
                if hasattr(cb, "onexception"):
                    stop = not not cb.onexception(self, exc_type, exc_value, exc_traceback)
            self.RaiseException = not stop
        for p in self.Chained:
            #print("forwarding exception to the chained promise...")
            p.exception(exc_type, exc_value, exc_traceback)
        self.wakeup()
        self._cleanup()

    @synchronized
    def cancel(self, cancel_chained = True):
        """Cancels the promise
        
        Args:
            cancel_chained (bool): whether to cancel chained promises too. Default = True
        """
        if not self.Cancelled:
            stop = False
            if self.OnCancel is not None:
                #print("calling OnException...")
                stop = not not self.OnCancel(self)
            for cb in self.Callbacks:
                if stop:
                    break
                if hasattr(cb, "oncancel"):
                    stop = not not cb.oncancel(self)
            if cancel_chained:
                for p in self.Chained:
                    p.cancel()
        self.Cancelled = True
        self.wakeup()
        self._cleanup()

    @synchronized
    def wait(self, timeout=None):
        """Blocks until the promise closes (completes, fails or gets cancelled).
        
        Args:
            timeout (numeric): Time-out in seconds. If the operation times out, the RuntimeError exception will be raised.
        
        Returns:
            Object: promise result, if the promise completes successfully. If the promsie is cancelled, None is returned.
        
        Raises:
            If the promise fails with an exception and the exception was not handled by one of the promise's callbacks,
            then the original exception will be raised.
        """
        
        #print("thread %s: wait(%s)..." % (get_ident(), self))
        pred = lambda x: x.Complete or x.Cancelled or self.ExceptionInfo is not None
        self.sleep_until(pred, self, timeout=timeout)
        try:
            if self.Complete:
                return self.Result
            elif self.Cancelled:
                return None
            elif self.ExceptionInfo:
                if self.RaiseException:
                    _, e, tb = self.ExceptionInfo
                    raise e.with_traceback(tb)
            else:
                raise Timeout()
        finally:
            self._cleanup()

    def _cleanup(self):
        self.Chained = []
        self.Callbacks = []
        self.OnException = self.OnComplete = None

    @staticmethod
    def all(*args):
        """Static method to create an ``ANDPromise`` - a promise-like object, which represents completion of all the argument promsies. 
        
        Args:
            *args: promise objects to combine
        """
        
        if args and isinstance(args[0], (tuple, list)):
            promises = args[0]
        else:
            promises = args
        return ANDPromise(promises)

    @staticmethod
    def any(*args):
        """Static method to create an ``ORPromise`` - a promise-like object, which represents completion of one of the argument promsies. 
        
        Args:
            *args: promise objects to combine
        """
        if args and isinstance(args[0], (tuple, list)):
            promises = args[0]
        else:
            promises = args
        return ORPromise(promises)
    
class ORPromise(Primitive):
    
    def __init__(self, promises):
        Primitive.__init__(self)
        self.Fulfilled = None
        for p in promises:
            p.addCallback(self)

    @synchronized
    def oncomplete(self, promise, result):
        if self.Fulfilled is None:
            self.Fulfilled = promise
            self.wakeup()

    @synchronized
    def wait(self, timeout = None):
        while self.Fulfilled is None:
            self.sleep(timeout)
        return self.Fulfilled.Result

class ANDPromise(Primitive):
    
    def __init__(self, promises):
        Primitive.__init__(self)
        self.Promises = promises
        
    def wait(self, timeout=None):
        return [p.wait(timeout) for p in self.Promises]
