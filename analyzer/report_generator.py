"""render a classified CrashReport as a Markdown
report suitable for attaching to a bug ticket or a postmortem doc.
"""
from __future__ import annotations

from datetime import datetime, timezone

from models import CrashReport


def generate_markdown(report: CrashReport) -> str:
    lines = []
    lines.append(f"# Kernel Crash Report")
    lines.append("")
    lines.append(f"- **Generated:** {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- **vmcore:** `{report.vmcore_path}`")
    if report.vmlinux_path:
        lines.append(f"- **vmlinux:** `{report.vmlinux_path}`")
    lines.append(f"- **Analysis engine:** {report.engine}")
    lines.append("")

    lines.append("## Classification")
    lines.append("")
    if report.classification:
        conf_pct = f"{report.classification_confidence * 100:.0f}%" \
            if report.classification_confidence is not None else "n/a"
        lines.append(f"**{report.classification}** (confidence: {conf_pct})")
        lines.append("")
        if report.classification_evidence:
            lines.append("Evidence:")
            for reason in report.classification_evidence:
                lines.append(f"- {reason}")
    else:
        lines.append("_Not classified - run classifier.classify() first._")
    lines.append("")

    lines.append("## Crash Context")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Crashing process | {report.comm or 'unknown'} (pid {report.pid or '?'}) |")
    lines.append(f"| CPU | {report.cpu if report.cpu is not None else 'unknown'} |")
    lines.append(f"| Oops type | {report.oops_type or 'unknown'} |")
    lines.append(f"| Faulting function | {report.faulting_function or 'unknown'} |")
    lines.append("")

    if report.panic_message:
        lines.append("## Panic Message")
        lines.append("")
        lines.append("```")
        lines.append(report.panic_message)
        lines.append("```")
        lines.append("")

    lines.append("## Backtrace")
    lines.append("")
    if report.backtrace:
        lines.append("```")
        for frame in report.backtrace:
            lines.append(str(frame))
        lines.append("```")
    else:
        lines.append("_No backtrace available._")
    lines.append("")

    if report.modules_loaded:
        lines.append("## Loaded Modules")
        lines.append("")
        lines.append(", ".join(f"`{m}`" for m in report.modules_loaded))
        lines.append("")

    return "\n".join(lines)


def write_report(report: CrashReport, output_path: str) -> None:
    with open(output_path, "w") as f:
        f.write(generate_markdown(report))
