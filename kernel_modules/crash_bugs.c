/* deliberate, specific kernel bugs, one per function.
 */
#include <linux/kernel.h>
#include <linux/slab.h>
#include <linux/spinlock.h>
#include <linux/string.h>
#include <linux/compiler.h>
#include "crashlab.h"


void crashlab_null_deref(void)
{
	int *ptr = NULL;

	pr_info("crashlab: triggering NULL pointer dereference\n");
	*(volatile int *)ptr = 0xdead;
}


void crashlab_use_after_free(void)
{
	int *ptr = kmalloc(sizeof(*ptr), GFP_KERNEL);

	if (!ptr) {
		pr_err("crashlab: allocation failed, cannot demo use-after-free\n");
		return;
	}

	pr_info("crashlab: triggering use-after-free\n");
	kfree(ptr);

	
	*(volatile int *)ptr = 0xdead;
}

// Self deadlock
static DEFINE_SPINLOCK(crashlab_lock);

void crashlab_deadlock(void)
{
	pr_info("crashlab: triggering self-deadlock on a spinlock\n");
	spin_lock(&crashlab_lock);
	
	spin_lock(&crashlab_lock);
}


static noinline void crashlab_recurse(unsigned long depth)
{
	
	char buf[512];

	memset(buf, (int)(depth & 0xff), sizeof(buf));
	pr_debug("crashlab: recursion depth %lu\n", depth);

	crashlab_recurse(depth + 1);

	barrier();
	(void)buf[0];
}

void crashlab_stack_overflow(void)
{
	pr_info("crashlab: triggering stack overflow via unbounded recursion\n");
	crashlab_recurse(0);
}

void crashlab_panic(void)
{
	pr_info("crashlab: triggering explicit panic()\n");
	panic("crashlab: deliberate panic() for crash-dump testing\n");
}

void crashlab_bug(void)
{
	pr_info("crashlab: triggering BUG()\n");
	BUG();
}

void crashlab_warn(void)
{
	pr_info("crashlab: triggering WARN_ON() (non-fatal, does not crash)\n");
	WARN_ON(1);
}
