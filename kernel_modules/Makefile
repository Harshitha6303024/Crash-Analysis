# builds crashlab.ko as a standard out-of-tree kbuild module.


obj-m += crashlab.o
crashlab-y := crashlab_main.o crash_bugs.o

KDIR ?= /lib/modules/$(shell uname -r)/build
PWD  := $(shell pwd)

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean

load:
	sudo insmod crashlab.ko
	sudo dmesg | tail -5

unload:
	sudo rmmod crashlab

.PHONY: all clean load unload
