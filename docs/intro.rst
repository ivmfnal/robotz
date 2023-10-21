PyThreader
==========


``PyThreader`` is a Python framework for developing threaded applications. It is built on top of standard Python ``therading`` library module.
Its purpose is to simplify threaded application development by providing a collection of useful classes implementing some basic
inter-thread synchronization and communication functions.

PyThreader ``Primitive``
------------------------

All PyThreader classes are subclasses of ``Primitive`` class, which combines the functionaity of three standard Python ``threading`` library classes:
``Lock``, ``Condition`` and ``Semaphore``. The ``Primitive`` class can be used as is or as a base class for other user-defined classes.



``PyThreader`` classes
----------------------

    * **PyThread** - combination of the ``Primtive`` and standard Python ``threading.Trhread``
    * **Timer** - enhancement of the standard ``threading.Timer``
    * **Promise** - similar to JavaScript ``Promise``, but with modifications reflecting the differences between Python and JavaScipt threading models
    * **TaskQueue** - a mechanism to run and manage concurrent ``Tasks`` - lightweight, short lived threads
    * **Scheduler** - an object which can be used to schedule one-time or periodic jobs executed on concurrent threads
    * **Producer** - an abstraction of a multi-threaded producer of abstract *items* with an internal ``TaskQueue``
    * **Processor** - a multi-threaded consumer and/or processor of abstract *items*, capable of sending them to another Processor
    * **Escrow** - a mechanism for 2 threads to communicate in synchronous way
    * **Flag** - simple object with a variable value, which a thread can wait for
    * **Gate** - a combination of `threading.Event` and `threading.Condition` objects

