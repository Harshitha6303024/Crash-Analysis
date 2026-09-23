"""confirms generate_markdown() produces
sane, complete output from a classified CrashReport.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analyzer"))

from models import CrashReport, StackFrame 
import classifier  
import report_generator  


class TestReportGenerator(unittest.TestCase):

    def setUp(self):
        self.report = CrashReport(
            vmcore_path="/var/crash/127.0.0.1-2026-09-22-10:00/vmcore",
            vmlinux_path="/usr/lib/debug/boot/vmlinux-6.8.0",
            engine="drgn",
        )
        self.report.comm = "bash"
        self.report.pid = 4821
        self.report.cpu = 2
        self.report.oops_type = "NULL pointer dereference"
        self.report.panic_message = "BUG: kernel NULL pointer dereference, address: 0000000000000000"
        self.report.backtrace = [
            StackFrame(index=0, function="crashlab_null_deref", offset="+0x9/0x20", module="crashlab"),
            StackFrame(index=1, function="crashlab_trigger_write", offset="+0x45/0x60", module="crashlab"),
            StackFrame(index=2, function="vfs_write", offset="+0xa1/0x1b0"),
        ]
        self.report.modules_loaded = ["crashlab", "nf_conntrack"]
        classifier.classify(self.report)

    def test_markdown_contains_classification(self):
        md = report_generator.generate_markdown(self.report)
        self.assertIn("NULL_POINTER_DEREF", md)

    def test_markdown_contains_backtrace_frames(self):
        md = report_generator.generate_markdown(self.report)
        self.assertIn("crashlab_null_deref", md)
        self.assertIn("vfs_write", md)

    def test_markdown_contains_context_table(self):
        md = report_generator.generate_markdown(self.report)
        self.assertIn("bash", md)
        self.assertIn("4821", md)

    def test_markdown_contains_evidence(self):
        md = report_generator.generate_markdown(self.report)
        self.assertIn("Evidence", md)

    def test_write_report_to_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "report.md")
            report_generator.write_report(self.report, out_path)
            self.assertTrue(os.path.exists(out_path))
            with open(out_path) as f:
                content = f.read()
            self.assertIn("Kernel Crash Report", content)


if __name__ == "__main__":
    unittest.main()
