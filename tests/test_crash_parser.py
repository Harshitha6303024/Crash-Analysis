"""analyzes crash_analyzer's text parsing
functions against realistic synthetic output from the `crash` utility,
without needing the real binary or a vmcore.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "analyzer"))

import crash_analyzer 


SAMPLE_BT_OUTPUT = '''
PID: 4821   TASK: ffff9a1b2c3d4e50  CPU: 2   COMMAND: "bash"
 #0 [ffffb2c140abcde0] crashlab_null_deref+0x9/0x20 [crashlab]
 #1 [ffffb2c140abcdf0] crashlab_trigger_write+0x45/0x60 [crashlab]
 #2 [ffffb2c140abce10] vfs_write+0xa1/0x1b0
 #3 [ffffb2c140abce40] ksys_write+0x5f/0xe0
 #4 [ffffb2c140abce70] do_syscall_64+0x3b/0x90
 #5 [ffffb2c140abcea0] entry_SYSCALL_64_after_hwframe+0x44/0xa9
'''

SAMPLE_LOG_OUTPUT = '''
[  123.456789] crashlab: dispatching 'null_deref' (NULL pointer dereference)
[  123.456800] BUG: kernel NULL pointer dereference, address: 0000000000000000
[  123.456810] #PF: supervisor write access in kernel mode
[  123.457000] RIP: 0010:crashlab_null_deref+0x9/0x20 [crashlab]
[  123.460000] Kernel panic - not syncing: Fatal exception
'''

SAMPLE_MOD_OUTPUT = '''
     MODULE       NAME         SIZE  OBJECT FILE
0xffffffffc0abc000  crashlab     16384  crashlab.ko
0xffffffffc0def000  nf_conntrack 180224 nf_conntrack.ko
'''


class TestCrashParser(unittest.TestCase):

    def test_parse_bt_header(self):
        pid, cpu, comm, frames = crash_analyzer.parse_bt_output(SAMPLE_BT_OUTPUT)
        self.assertEqual(pid, 4821)
        self.assertEqual(cpu, 2)
        self.assertEqual(comm, "bash")

    def test_parse_bt_frames(self):
        _, _, _, frames = crash_analyzer.parse_bt_output(SAMPLE_BT_OUTPUT)
        self.assertEqual(len(frames), 6)
        self.assertEqual(frames[0].function, "crashlab_null_deref")
        self.assertEqual(frames[0].offset, "+0x9/0x20")
        self.assertEqual(frames[0].module, "crashlab")
        self.assertEqual(frames[2].function, "vfs_write")
        self.assertIsNone(frames[2].module)

    def test_parse_log_output(self):
        panic_message, oops_type = crash_analyzer.parse_log_output(SAMPLE_LOG_OUTPUT)
        self.assertIn("Kernel panic", panic_message)
        
        self.assertEqual(oops_type, "NULL pointer dereference")

    def test_parse_mod_output(self):
        modules = crash_analyzer.parse_mod_output(SAMPLE_MOD_OUTPUT)
        self.assertIn("crashlab", modules)
        self.assertIn("nf_conntrack", modules)

    def test_end_to_end_parsing_feeds_classifier(self):
        
        import classifier
        from models import CrashReport

        pid, cpu, comm, frames = crash_analyzer.parse_bt_output(SAMPLE_BT_OUTPUT)
        panic_message, oops_type = crash_analyzer.parse_log_output(SAMPLE_LOG_OUTPUT)

        report = CrashReport(vmcore_path="/fake", engine="crash")
        report.pid, report.cpu, report.comm = pid, cpu, comm
        report.backtrace = frames
        report.panic_message, report.oops_type = panic_message, oops_type

        classifier.classify(report)
        self.assertEqual(report.classification, classifier.NULL_POINTER_DEREF)


if __name__ == "__main__":
    unittest.main()
