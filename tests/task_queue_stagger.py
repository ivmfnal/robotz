import time
from pythreader import Task, TaskQueue
from pythreader.core import printWaiting
from threading import Timer

import random

class T(Task):
	def __init__(self, id):
		Task.__init__(self)
		self.Id = id

	def run(self):
	    print ("task %d: t=%s" % (self.Id, time.ctime(time.time())))

tq = TaskQueue(1, capacity=10, stagger=1.0)

def printStats():
	with tq:
		printWaiting()


for i in range(100):
	t = T(i)
	print ("submitting task %d..." % (i,))
	tq << t
	print ("task %d submitted" % (i,))
	time.sleep(0.2+random.random())
	if i and i % 10 == 0:
		Timer(0.5, printStats).start()
		

tq.waitUntilEmpty()
