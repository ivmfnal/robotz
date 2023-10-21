from pythreader import Processor
import time, random

class MyProcessor(Processor):
    
    def process(self, x):
        time.sleep(random.random()*0.5)
        return x**2
        
processor = MyProcessor(5)

promises = [processor.put(i) for i in range(100)]
for p in promises:
    print(p.Data, "->", p.wait())