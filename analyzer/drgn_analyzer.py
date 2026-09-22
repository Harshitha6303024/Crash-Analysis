"""extract a CrashReport from a vmcore using drgn.
"""
from __future__ import annotations

from typing import Optional

from models import CrashReport, StackFrame


def analyze(vmcore_path: str, vmlinux_path: str) -> CrashReport:
    """Open `vmcore_path` with drgn and populate a CrashReport."""
    try:
        import drgn
        from drgn import Program
    except ImportError as exc:
        raise RuntimeError(
            "drgn is not installed. Run: pip install drgn"
        ) from exc

    report = CrashReport(
        vmcore_path=vmcore_path,
        vmlinux_path=vmlinux_path,
        engine="drgn",
    )

    prog = Program()
    prog.set_core_dump(vmcore_path)
    
    prog.load_debug_info([vmlinux_path])

   
    try:
        from drgn.helpers.linux.printk import get_printk_records
        records = list(get_printk_records(prog))
        log_lines = [r.text.decode(errors="replace") for r in records[-50:]]
        report.panic_message = _extract_panic_line(log_lines)
        report.oops_type = _classify_oops_type(log_lines)
    except Exception:
        
        report.panic_message = None

    # Crashing thread 
    thread = prog.crashed_thread()
    report.pid = thread.pid.value_()
    try:
        report.comm = thread.object.comm.string_().decode()
    except Exception:
        report.comm = None

    trace = prog.stack_trace(thread)
    for i, frame in enumerate(trace):
        name = frame.name if frame.name else "??"
        try:
            sym = frame.pc  
            address = hex(sym)
        except Exception:
            address = None
        report.backtrace.append(
            StackFrame(index=i, function=name, address=address)
        )

    
    try:
        from drgn.helpers.linux.module import for_each_module
        report.modules_loaded = [
            m.name.string_().decode() for m in for_each_module(prog)
        ]
    except Exception:
        report.modules_loaded = []

    return report


def _extract_panic_line(log_lines: list) -> Optional[str]:
    for line in reversed(log_lines):
        if "Kernel panic" in line or "BUG:" in line or "kernel BUG at" in line:
            return line.strip()
    return log_lines[-1].strip() if log_lines else None


def _classify_oops_type(log_lines: list) -> Optional[str]:
    joined = "\n".join(log_lines)
    known_types = [
        "NULL pointer dereference",
        "general protection fault",
        "kernel BUG at",
        "soft lockup",
        "hung_task",
        "stack guard page",
        "use-after-free",
    ]
    for t in known_types:
        if t in joined:
            return t
    return None
