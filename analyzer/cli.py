#!/usr/bin/env python3
"""command-line entry point for the crash dump analyzer.


"""
from __future__ import annotations

import argparse
import sys

import classifier
import report_generator


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze a Linux kernel vmcore and classify the crash."
    )
    parser.add_argument("--vmcore", required=True, help="Path to the vmcore file")
    parser.add_argument("--vmlinux", required=True,
                         help="Path to the matching vmlinux (with debug info)")
    parser.add_argument("--engine", choices=["drgn", "crash"], default="drgn",
                         help="Analysis backend to use (default: drgn)")
    parser.add_argument("--crash-binary", default="crash",
                         help="Path to the `crash` executable (engine=crash only)")
    parser.add_argument("--output", default="crash_report.md",
                         help="Where to write the Markdown report")
    return parser


def main(argv=None) -> int:
    args = build_arg_parser().parse_args(argv)

    if args.engine == "drgn":
        import drgn_analyzer
        report = drgn_analyzer.analyze(args.vmcore, args.vmlinux)
    else:
        import crash_analyzer
        report = crash_analyzer.analyze(args.vmcore, args.vmlinux, args.crash_binary)

    classifier.classify(report)
    report_generator.write_report(report, args.output)

    print(f"Classification: {report.classification} "
          f"({(report.classification_confidence or 0) * 100:.0f}% confidence)")
    print(f"Faulting function: {report.faulting_function}")
    print(f"Full report written to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
