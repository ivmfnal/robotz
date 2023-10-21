from .core import Primitive, synchronized, Timeout

class Promise(Primitive):
    
    def __init__(self):
        Primitive.__init__(self, callback = None, callback_param = None)
        self.Done = False
        self.Payload = None
        self.Callback = callback
        self.CallbackParam = callback_param
        self.Cancelled = False
        
    @synchronized
    def cancel(self):
        self.Cancelled = True
        self.wakeup()
        
    @synchronized
    def wait(self, timeout=None):
        t1 = time.time() + timeout if timeout is not None else None
        while (t1 is None or time.time() < t1) and not self.Done and not self.Cancelled:
            dt = max(0.0, t1 - time.time()) if t1 is not None else None
            self.sleep(dt)
        if not self.Done and not self.Cancelled:
            raise Timeout()
            
    @synchronized
    def is_done(self):
        return self.Done
        
    @synchronized
    def done(self, payload=None):
        self.Payload = payload
        self.Done = True
        if not self.Cancelled and self.Callback is not None:
            try:
                self.Callback(self, payload, self.CallbackParam)
            except:
                pass
        self.wakeup()
        
