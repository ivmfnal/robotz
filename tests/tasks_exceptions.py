from pythreader import Task, TaskQueue
import sys, traceback

class TaskOK(Task):
    
    def run(self):
        print(">>> TaskOK: OK")
        
    def __str__(self):
        return "Task<OK>"
        
class TaskError(Task):
    
    def run(self):
        print(">>> TaskError: generating exception")
        raise ValueError("Generated ValueError")
        
    def __str__(self):
        return "Task<Error>"
        

class Delegate(object):

    def taskFailed(self, queue, task, etype, evalue, etb):
        print(f"Delegate: exception reported in task {task}")
        traceback.print_exception(etype, evalue, etb)
        
    def taskEnded(self, queue, task):
        print(f"Delegate: task ended: {task}")
        
        
d = Delegate()

q1 = TaskQueue(2)
q2 = TaskQueue(2, delegate = d)
tok = TaskOK()
terr = TaskError()


print("-------- Queue without delegae --------")
for _ in range(100):
    q1 << tok << terr
q1.join()

print("-------- Queue with delegae --------")
for _ in range(100):
    q2 << tok << terr
q2.join()





        
