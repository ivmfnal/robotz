from pythreader import Scheduler
import time, traceback
from datetime import datetime

s = Scheduler()

class NTimes(object):

    def __init__(self, n):
        self.N = n
    
    def __call__(self, message):
        t = datetime.now()
        print("%s: %s" % (t.strftime("%H:%M:%S.%f"), message))
        self.N -= 1
        if self.N <= 0:
            print("stopping", message)
            return "stop"
        
s.start()
time.sleep(1.0)
s.add(NTimes(10), 1.5, "green 1.5 sec")
print("+++added green")
time.sleep(1.0)
s.add(NTimes(7), 0.5, "blue 0.5 sec")
print("+++added blue")


time.sleep(20.0)
s.add(NTimes(10), 0.25, "red 0.25 sec", t0=0)
print("+++red green")

s.join()

        