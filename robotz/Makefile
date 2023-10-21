FILES = \
    core.py  __init__.py  dequeue.py  Subprocess.py  task_queue.py Version.py \
    RWLock.py promise.py Scheduler.py processor.py gate.py flag.py LogFile.py producer.py escrow.py gang.py

LIB_DIR = $(BUILD_DIR)/pythreader

build: $(LIB_DIR)
	cp $(FILES) $(LIB_DIR)
	mkdir -p $(LIB_DIR)/tools
	cp tools/*.py $(LIB_DIR)/tools
    
$(LIB_DIR):
	mkdir -p $@

    
