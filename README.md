# Crash-Analysis
Kernel Crash Dump Analysis Toolkit

A Linux kernel debugging that reproduces crashes in a disposable VM, captures the resulting vmcore with kdump, and analyzes it using crash or drgn.

The toolkit extracts the faulting function, call stack, and process context, then generates a short report. It also uses evidence from the crash log and stack trace to suggest a bug category, such as a NULL dereference, memory corruption, or deadlock.
