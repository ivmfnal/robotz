import threading
from pythreader import RWLock

if __name__ == '__main__':
    import random, time
    
    class T(threading.Thread):
        
        Interlock = threading.RLock()
        
        @classmethod
        def printStats(cls, lock):
            with cls.Interlock:
                exclusive, shared = lock.owners()
                print (exclusive, len(shared))
                
        
        def __init__(self, lock):
            threading.Thread.__init__(self)
            self.Lock = lock
        
        def run(self):
            while True:
                if random.random() < 0.2:
                    with self.Lock.exclusive:
                        print ("exclusive")
                        self.printStats(self.Lock)
                        time.sleep(random.random() * 5.0)
                        self.printStats(self.Lock)
                else:
                    with self.Lock.shared:
                        print ("shared")
                        self.printStats(self.Lock)
                        time.sleep(random.random() * 5.0)
                        self.printStats(self.Lock)
                    
    l = RWLock()
    nt = 10
    threads = [T(l) for _ in range(nt)]
    for t in threads:
        t.start()
        
    for t in threads:
        t.join()
    
    
    
    
    
