"""exercises classifier.classify() against synthetic
CrashReport objects, so it runs with zero dependencies 
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analyzer"))

from models import CrashReport, StackFrame  
import classifier  


def make_report(backtrace_funcs, oops_type=None, panic_message=None):
    report = CrashReport(vmcore_path="/fake/vmcore", engine="test")
    report.oops_type = oops_type
    report.panic_message = panic_message
    report.backtrace = [
        StackFrame(index=i, function=fn) for i, fn in enumerate(backtrace_funcs)
    ]
    return report


class TestClassifier(unittest.TestCase):

    def test_null_deref_by_function_name(self):
        report = make_report(["crashlab_null_deref", "crashlab_trigger_write", "vfs_write"])
        classifier.classify(report)
        self.assertEqual(report.classification, classifier.NULL_POINTER_DEREF)
        self.assertGreater(report.classification_confidence, 0.9)
        self.assertTrue(report.classification_evidence)

    def test_use_after_free_by_function_name(self):
        report = make_report(["crashlab_use_after_free", "crashlab_trigger_write"])
        classifier.classify(report)
        self.assertEqual(report.classification, classifier.USE_AFTER_FREE)

    def test_deadlock_by_function_name(self):
        report = make_report(["crashlab_deadlock", "crashlab_trigger_write"])
        classifier.classify(report)
        self.assertEqual(report.classification, classifier.DEADLOCK_OR_HANG)

    def test_stack_overflow_by_recursion_shape(self):
        
        funcs = ["some_driver_recurse"] * 20 + ["do_syscall_64"]
        report = make_report(funcs)
        classifier.classify(report)
        self.assertEqual(report.classification, classifier.STACK_OVERFLOW)
        self.assertIn("consecutive frames", report.classification_evidence[0])

    def test_null_deref_by_oops_text_when_no_known_function(self):
        report = make_report(
            ["some_unknown_driver_func", "do_page_fault"],
            oops_type="NULL pointer dereference",
        )
        classifier.classify(report)
        self.assertEqual(report.classification, classifier.NULL_POINTER_DEREF)

    def test_soft_lockup_text(self):
        report = make_report(
            ["some_func"],
            panic_message="watchdog: BUG: soft lockup - CPU#2 stuck for 22s!",
        )
        classifier.classify(report)
        self.assertEqual(report.classification, classifier.DEADLOCK_OR_HANG)

    def test_explicit_bug_assertion_text(self):
        report = make_report(
            ["some_func"],
            oops_type="kernel BUG at drivers/foo/bar.c:123",
        )
        classifier.classify(report)
        self.assertEqual(report.classification, classifier.EXPLICIT_BUG_ASSERTION)

    def test_spinlock_self_deadlock_structural_fallback(self):
        # No text hints, no known function names - just two lock-acquire
        # frames back to back, simulating an unrecognized self-deadlock.
        report = make_report(["_raw_spin_lock", "_raw_spin_lock", "some_driver_ioctl"])
        classifier.classify(report)
        self.assertEqual(report.classification, classifier.DEADLOCK_OR_HANG)

    def test_unknown_when_nothing_matches(self):
        report = make_report(["totally_unrelated_function", "another_one"])
        classifier.classify(report)
        self.assertEqual(report.classification, classifier.UNKNOWN)
        self.assertEqual(report.classification_confidence, 0.0)

    def test_evidence_is_always_populated(self):
        for funcs, oops in [
            (["crashlab_null_deref"], None),
            (["unknown_func"], "general protection fault"),
            (["x"], None),
        ]:
            report = make_report(funcs, oops_type=oops)
            classifier.classify(report)
            self.assertTrue(report.classification_evidence,
                             f"No evidence recorded for {funcs}, {oops}")


if __name__ == "__main__":
    unittest.main()
