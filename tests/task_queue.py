import time, random
from pythreader import TaskQueue, Task
from threading import Timer
import uuid

class MyTask(Task):

    def __init__(self):
        Task.__init__(self)
        self.Id = uuid.uuid4().hex[:5]

    def run(self):
        print (time.time(), ":", self.Id, "started")
        time.sleep(random.random()*0.5)
        print (self.Id, "ended")

q = TaskQueue(5, stagger=0.0001, capacity=30)

promises = [q.append(MyTask(), after=random.random()).promise for _ in range(100)]
for _ in range(100):
    time.sleep(random.random()/10)
    promises.append(q.append(MyTask(), after=random.random()).promise)

assert len(promises) == 200
for p in promises:
    p.wait()
    print("Queue counts:", q.counts())
print("All promises fulfilled")

q.waitUntilEmpty()
print("The queue is empty")
