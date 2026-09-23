# Root convenience Makefile 

.PHONY: module test clean

module:
	$(MAKE) -C kernel_modules

test:
	cd tests && python3 -m unittest discover -v

clean:
	$(MAKE) -C kernel_modules clean
