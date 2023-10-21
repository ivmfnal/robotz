from pythreader import Processor, Flag
import random
from threading import Condition

done = Flag()

class MyProcessor(Processor):
    
    def __init__(self, name, nworkers, output = None):
        Processor.__init__(self, nworkers, output = output, name=name)

    def process(self, lst):
        lst.append(self.Name)
        if random.random() < 0.2:
            done.value = "done"
            return None
        else:
            return lst

p1 = MyProcessor("A", 2)
p2 = MyProcessor("B", 2, output = p1)
p1.Output = p2

lst = []
p1.put(lst)

done.sleep_until("done")

print("Result:", lst)