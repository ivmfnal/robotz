import random, time, uuid
from pythreader import Processor, PyThread


class MyProcessor(Processor):
    """
    Simple processor
    """

    def process(self, item):
        return "%s -> %s" % (item, item[::-1])

processor = MyProcessor()

# test it quickly
processor.put("hello!")
print("Simple hello test output:", processor.get())

class Producer(PyThread):
    """
    Producer which will feed our processor with some items to process
    """
    def __init__(self, processor, n, sleep_between_items):
        PyThread.__init__(self)
        self.Processor = processor
        self.N = n
        self.Delay = sleep_between_items
    
    def run(self):
        for _ in range(self.N):
            if self.Delay:
                time.sleep(random.random())
            self.Processor.put(uuid.uuid4().hex[:4])
        self.Processor.close()
        print(f"producer: {self.N} items sent. Processor closed")

for run in range(1, 4):
    print("\n--- Starting run", run, "---")
    processor.open()
    producer = Producer(processor, 10, run%2)
    producer.start()
    n = 0
    for out in processor:
        print(out)
        n += 1
    print(f"producer output ended. {n} items received")
    producer.join()
    print("--- Ended or run", run, "---")




