/* registers a debugf interface that
 * dispatches to the individual bug functions

 */
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/init.h>
#include <linux/debugfs.h>
#include <linux/uaccess.h>
#include <linux/string.h>
#include <linux/errno.h>
#include "crashlab.h"

#define CRASHLAB_MAX_CMD_LEN 32

struct crashlab_bug_entry {
	const char *name;
	void (*trigger)(void);
	const char *description;
};

static const struct crashlab_bug_entry crashlab_bugs[] = {
	{ "null_deref",     crashlab_null_deref,     "NULL pointer dereference" },
	{ "use_after_free", crashlab_use_after_free, "Use-after-free write" },
	{ "deadlock",       crashlab_deadlock,       "Self-deadlock on a spinlock (hang, not panic)" },
	{ "stack_overflow", crashlab_stack_overflow, "Unbounded recursion / stack overflow" },
	{ "panic",          crashlab_panic,          "Explicit panic() call" },
	{ "bug",            crashlab_bug,            "BUG() assertion failure" },
	{ "warn",           crashlab_warn,           "WARN_ON() - non-fatal, for comparison" },
};

static struct dentry *crashlab_dir;

static ssize_t crashlab_trigger_write(struct file *file, const char __user *ubuf,
				       size_t count, loff_t *ppos)
{
	char cmd[CRASHLAB_MAX_CMD_LEN];
	size_t len = min(count, sizeof(cmd) - 1);
	int i;

	if (copy_from_user(cmd, ubuf, len))
		return -EFAULT;
	cmd[len] = '\0';

	/* strip trailing newline from `echo foo > trigger` */
	if (len > 0 && cmd[len - 1] == '\n')
		cmd[len - 1] = '\0';

	for (i = 0; i < ARRAY_SIZE(crashlab_bugs); i++) {
		if (strcmp(cmd, crashlab_bugs[i].name) == 0) {
			pr_info("crashlab: dispatching '%s' (%s)\n",
				crashlab_bugs[i].name,
				crashlab_bugs[i].description);
			crashlab_bugs[i].trigger();
			/* Most triggers never return (they crash/hang the
			 * kernel). Only "warn" falls through to here. */
			return count;
		}
	}

	pr_warn("crashlab: unknown trigger '%s' (see .../crashlab/list)\n", cmd);
	return -EINVAL;
}

static ssize_t crashlab_list_read(struct file *file, char __user *ubuf,
				   size_t count, loff_t *ppos)
{
	char buf[512];
	int len = 0;
	int i;

	for (i = 0; i < ARRAY_SIZE(crashlab_bugs); i++)
		len += scnprintf(buf + len, sizeof(buf) - len, "%-16s %s\n",
				  crashlab_bugs[i].name,
				  crashlab_bugs[i].description);

	return simple_read_from_buffer(ubuf, count, ppos, buf, len);
}

static const struct file_operations crashlab_trigger_fops = {
	.owner = THIS_MODULE,
	.write = crashlab_trigger_write,
};

static const struct file_operations crashlab_list_fops = {
	.owner = THIS_MODULE,
	.read  = crashlab_list_read,
};

static int __init crashlab_init(void)
{
	crashlab_dir = debugfs_create_dir("crashlab", NULL);
	if (IS_ERR(crashlab_dir)) {
		pr_err("crashlab: failed to create debugfs directory (%ld)\n",
		       PTR_ERR(crashlab_dir));
		return PTR_ERR(crashlab_dir);
	}

	debugfs_create_file("trigger", 0200, crashlab_dir, NULL,
			     &crashlab_trigger_fops);
	debugfs_create_file("list", 0444, crashlab_dir, NULL,
			     &crashlab_list_fops);

	pr_info("crashlab: loaded.\n");
	pr_info("crashlab:   cat  /sys/kernel/debug/crashlab/list\n");
	pr_info("crashlab:   echo <bug_name> > /sys/kernel/debug/crashlab/trigger\n");
	return 0;
}

static void __exit crashlab_exit(void)
{
	debugfs_remove_recursive(crashlab_dir);
	pr_info("crashlab: unloaded\n");
}

module_init(crashlab_init);
module_exit(crashlab_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("Kernel Crash Dump Analysis Toolkit");
MODULE_DESCRIPTION("Deliberately triggers specific kernel bugs, on demand, for crash-dump analysis training");
