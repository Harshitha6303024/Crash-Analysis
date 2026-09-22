/* declarations for the individual bug-trigger functions.

 */
#ifndef _CRASHLAB_H
#define _CRASHLAB_H

void crashlab_null_deref(void);
void crashlab_use_after_free(void);
void crashlab_deadlock(void);
void crashlab_stack_overflow(void);
void crashlab_panic(void);
void crashlab_bug(void);
void crashlab_warn(void);

#endif /* _CRASHLAB_H */
