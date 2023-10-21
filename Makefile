BUILD_DIR = $(HOME)/build/pythreader
TAR_DIR = /tmp/$(USER)
TAR_FILE = $(TAR_DIR)/pythreader_$(VERSION).tar

all:
	make VERSION=`python pythreader/Version.py` all_with_version_defined
	
clean:
	rm -rf $(BUILD_DIR) $(TAR_FILE)

all_with_version_defined:	tarball
	
    
build: $(BUILD_DIR)
	cd pythreader; make BUILD_DIR=$(BUILD_DIR) build
	cd tests; make BUILD_DIR=$(BUILD_DIR) build
	cd tools; make BUILD_DIR=$(BUILD_DIR) build
    
tarball: clean build $(TAR_DIR)
	cd $(BUILD_DIR); tar cf $(TAR_FILE) *
	@echo 
	@echo Tar file $(TAR_FILE) is ready
	@echo 


$(BUILD_DIR):
	mkdir -p $@
    
$(TAR_DIR):
	mkdir -p $@

