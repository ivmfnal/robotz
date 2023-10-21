PyThreader Primitive
====================

All PyThreader classes are subclasses of ``Primitive`` class, which combines the functionaity of three standard Python ``threading`` library classes:
``Lock``, ``Condition`` and ``Semaphore``. The ``Primitive`` class can be used as is or as a base class for other user-defined classes.
In addition, ``Primitive`` object can have a name.

Lock functionality
------------------

A ``Primitive`` has its own Lock object and exports its functionality through the context interface. 
When a primitive is created, by default, it creates its own ``threaing.RLock`` object. Otherwise, a primitive
can use a user-provided Lock or RLock object:

    .. code-block:: python
    
        my_primitive = Primitive()          # - will create and use its own RLock object
        
        my_lock = threading.Lock()
        my_other_primitive = Primitive(lock=my_lock)
        
Lock objects can be shared by ``Primitives``:

    
    .. code-block:: python

        my_lock = threading.Lock()
        p1 = Primitive(lock=my_lock)
        p2 = Primitive(lock=my_lock)        
        p3 = Primitive(lock=p2.getLock())   # share the same Lock object by 3 primtives

A ``Primtive`` object can be used as a context. Any piece of code executed by the thread inside the ``Primtive``'s context will be 
executed while the lock is exclusively locked by the thread:

    .. code-block:: python
    
        my_primitive = Primitive()
        with my_primitive:
            ... # this code will be executed while the primitive is locked
        ... # and then the primitive will be unlocked

``Primitive`` also provides a way to temporarily unlock itself:

    .. code-block:: python
    
        my_primitive = Primitive()
        with my_primitive:
            ... # this code will be executed while the primitive is locked
            with my_primitive.unlock:
                # unlock the primitive temporarily
                ... # execute some code while the primitive is unlocked
            # lock the primitive again
            ... # do something else while the primitive is locked again
        ... # and then the primitive will be unlocked
        
Another way to execute a code inside the ``Primitive``'s lock context is inherit from the ``Primitive`` class and use ``synchronized`` decorator:

    .. code-block:: python

        class Widget(Primitive):
        
            @synchronized
            def critical(self, params):
                # this code will be executed while the lock is locked
                ...
                
The decorator is simply a convenient way to do this:

    .. code-block:: python

        class Widget(Primitive):
        
            def critical(self, params):
                with self:
                    # this code will be executed while the lock is locked
                    ...

The ``unlock`` attribute of the ``Primitive`` can be used within a synchronized method:

    .. code-block:: python

        class Widget(Primitive):
        
            @synchronized
            def critical(self, params):
                # this code will be executed while the lock is locked
                ...
                with self.unlock:
                    # unlock the lock and do sometbhing else
                    ...
                    # then lock it again
                ... # and continue locked
                
As you can see, the ``synchronized`` decorator is very similar to Java ``synchronized`` method attribute 
                
Semaphore functionality
-----------------------
Any ``Primitive`` has its own Semaphore object. By default the internal semaphore has initial value 1, but that can be changed using
optional ``gate`` argument passed to the ``Primitive`` constructor

    .. code-block:: python

        class MyGate(Primitive):
        
            def __init__(self):
                Primtivive.__init__(self, gate=5)
                
The ``Primitive``'s semaphore functionality is used via ``gated`` decorator:

    .. code-block:: python

        class MyGate(Primitive):
        
            def __init__(self):
                Primtivive.__init__(self, gate=5)       # set the "gate" capacity to 5
                
            @gated
            def gated_method(self, params):
                ... # this code will be executed by no more than 5 threads simultaneously

Condition functionality
-----------------------

``Primitive`` has functionality of ``threading.Condition`` via ``sleep``/``wakeup`` interface. A thread can "sleep" on the ``primtivive`` until the
some other thread "wakes" it up via the same ``primitive``. For example:

    .. code-block:: python

        class Producer(Primitive):
        
            def produce(self):
                ...
                self.Product = "done"
                self.wake_up(n=1)                   # wake up one of consumers waiting for the product, if any

        class Consumer:
        
            def consume(self, producer):
                producer.sleep()                    # wait for the producer to finish producution
                print("Product:", producer.Product)

A more sophisticated example would be waiting until a predicate is satisfied:

    .. code-block:: python

        class Producer(Primitive):
        
            def produce(self):
                color = "white"
                while True:
                    ...
                    self.Color = "red" if random.random() < 0.5 else "green"
                    self.wake_up(n=1)                   # wake up one of consumers waiting for the product, if any

        class Consumer:
        
            def consume(self, producer):
                producer.sleep_until(lambda p: p.Color == "green", producer) # wait until the product is ready and it is "green"
                print("green")


Alarms
------

``Primitive`` object also has simple "alarm" functionality implemented using ``Timer`` threads. A ``Primitive`` can start an alarm,
which will call specified function at given time and/or periodically at given intervals:

    .. code-block:: python

        class Clock(Primitive):
        
            def start_clock(self):
                self.alarm(self.tick, t=(int(time.time())+59)//60*60, interval=1.0)     # call my tick() method every second starting next minute
                
            def tick(self):
                print(time.ctime(time.time()))

A ``Primitive`` object can have only 1 alarm active at any given time. If an alarm is already active and a new alarm for the same
``Primitivive`` is created, the old alarm is cancelled.
