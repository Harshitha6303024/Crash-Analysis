"""extract a CrashReport using the classic `crash`
utility (package: crash / crashutils, depending on distro) instead of
drgn.
"""
from __future__ import annotations

import re
import subprocess
from typing import List, Optional

from models import CrashReport, StackFrame

_BT_HEADER_RE = re.compile(
    r'PID:\s*(\d+)\s+TASK:\s*\S+\s+CPU:\s*(\d+)\s+COMMAND:\s*"([^"]+)"'
)

_BT_FRAME_RE = re.compile(
    r'^\s*#(\d+)\s+\[(\S+)\]\s+(\S+?)'
    r'(?:\+([^ /]+/[^ ]+))?'
    r'(?: at (\S+))?'
    r'(?:\s+\[(\S+)\])?\s*$'
)

_KNOWN_OOPS_MARKERS = [
    "NULL pointer dereference",
    "general protection fault",
    "kernel BUG at",
    "soft lockup",
    "hung_task",
    "stack guard page",
    "use-after-free",
    "BUG: unable to handle kernel",
]


def analyze(vmcore_path: str, vmlinux_path: str, crash_binary: str = "crash") -> CrashReport:
    """Run `crash` in batch mode and populate a CrashReport from its output."""
    commands = "bt\nlog\nmod\nquit\n"
    try:
        proc = subprocess.run(
            [crash_binary, "-s", vmlinux_path, vmcore_path],
            input=commands,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"'{crash_binary}' not found. Install the 'crash' package "
            "for your distro, or use the drgn engine instead."
        ) from exc

    output = proc.stdout
    report = CrashReport(vmcore_path=vmcore_path, vmlinux_path=vmlinux_path, engine="crash")

    bt_section = _extract_section(output, "crash> bt", "crash>")
    pid, cpu, comm, frames = parse_bt_output(bt_section)
    report.pid, report.cpu, report.comm, report.backtrace = pid, cpu, comm, frames

    log_section = _extract_section(output, "crash> log", "crash>")
    report.panic_message, report.oops_type = parse_log_output(log_section)

    mod_section = _extract_section(output, "crash> mod", "crash>")
    report.modules_loaded = parse_mod_output(mod_section)

    return report


def _extract_section(full_output: str, start_marker: str, end_marker: str) -> str:
    """Pull the text between one `crash>` prompt and the next."""
    try:
        start = full_output.index(start_marker) + len(start_marker)
        end = full_output.index(end_marker, start)
        return full_output[start:end]
    except ValueError:
        return ""


def parse_bt_output(bt_text: str):
    """Parse `crash`'s `bt` command output into (pid, cpu, comm, frames)."""
    pid = cpu = None
    comm = None
    header = _BT_HEADER_RE.search(bt_text)
    if header:
        pid, cpu, comm = int(header.group(1)), int(header.group(2)), header.group(3)

    frames: List[StackFrame] = []
    for line in bt_text.splitlines():
        m = _BT_FRAME_RE.match(line)
        if not m:
            continue
        idx, address, func, offset, at_addr, module = m.groups()
        frames.append(StackFrame(
            index=int(idx),
            function=func,
            offset=("+" + offset) if offset else None,
            module=module,
            address=at_addr or address,
        ))
    return pid, cpu, comm, frames


def parse_log_output(log_text: str):
    """Return (panic_message, oops_type) found in `crash`'s `log` output."""
    lines = [l for l in log_text.splitlines() if l.strip()]
    panic_message = None
    oops_type = None

    for marker in _KNOWN_OOPS_MARKERS:
        for line in lines:
            if marker in line:
                oops_type = marker
                break
        if oops_type:
            break

    for line in reversed(lines):
        if "Kernel panic" in line or "BUG:" in line or "kernel BUG at" in line:
            panic_message = line.strip()
            break
    if panic_message is None and lines:
        panic_message = lines[-1].strip()

    return panic_message, oops_type


def parse_mod_output(mod_text: str) -> List[str]:
    """Parse `crash`'s `mod` command (module list) output."""
    modules = []
    for line in mod_text.splitlines():
        parts = line.split()
        # crash's `mod` output looks like: MODULE NAME SIZE OBJECT FILE
        # Skip the header row and blank lines.
        if len(parts) >= 2 and parts[0].startswith("0x"):
            modules.append(parts[1])
    return modules
