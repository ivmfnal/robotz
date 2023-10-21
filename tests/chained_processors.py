from pythreader import Processor
import random, time

class P1(Processor):
    
    def process(self, x):

        time.sleep(random.random()*0.5)
        return x+1
        
class P2(Processor):
    
    def process(self, x):
        time.sleep(random.random()*0.5)
        return x**2
        

p2 = P2(3, name="P2")
p1 = P1(3, output=p2, name="P1")

promises = [p1.put(x) for x in range(10)]

if False:
    for pr in promises:
        print(pr.Data, "->", pr.wait())
i = 0
for y in p2:
	print(y)
	i += 1
	if i > 3:
		break
print("reopened")
for y in p2:
        print(y)

