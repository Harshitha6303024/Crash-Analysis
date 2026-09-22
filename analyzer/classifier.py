"""classifier.py - given a populated CrashReport, decide what kind of
bug it is.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from models import CrashReport

NULL_POINTER_DEREF = "NULL_POINTER_DEREF"
USE_AFTER_FREE = "USE_AFTER_FREE"
DEADLOCK_OR_HANG = "DEADLOCK_OR_HANG"
STACK_OVERFLOW = "STACK_OVERFLOW"
EXPLICIT_BUG_ASSERTION = "EXPLICIT_BUG_ASSERTION"
GENERAL_PANIC = "GENERAL_PANIC"
UNKNOWN = "UNKNOWN"

# Recognize this project's own training-module function names directly.
# In a real fleet you'd extend this table with your own known-hot
# functions (e.g. specific driver entry points your team owns).
_KNOWN_FUNCTION_HINTS = {
    "crashlab_null_deref": (NULL_POINTER_DEREF, 0.99),
    "crashlab_use_after_free": (USE_AFTER_FREE, 0.99),
    "crashlab_deadlock": (DEADLOCK_OR_HANG, 0.99),
    "crashlab_stack_overflow": (STACK_OVERFLOW, 0.95),
    "crashlab_recurse": (STACK_OVERFLOW, 0.95),
    "crashlab_bug": (EXPLICIT_BUG_ASSERTION, 0.99),
    "crashlab_panic": (GENERAL_PANIC, 0.9),
}

_TEXT_HINTS = [
    # (substring to find in oops_type/panic_message, category, confidence)
    ("NULL pointer dereference", NULL_POINTER_DEREF, 0.9),
    ("use-after-free", USE_AFTER_FREE, 0.9),
    ("slab-use-after-free", USE_AFTER_FREE, 0.9),
    ("soft lockup", DEADLOCK_OR_HANG, 0.85),
    ("hung_task", DEADLOCK_OR_HANG, 0.85),
    ("stack guard page", STACK_OVERFLOW, 0.85),
    ("corrupted stack end", STACK_OVERFLOW, 0.8),
    ("kernel BUG at", EXPLICIT_BUG_ASSERTION, 0.85),
    ("general protection fault", USE_AFTER_FREE, 0.5),  # common UAF symptom
    ("Kernel panic", GENERAL_PANIC, 0.4),
]

_RECURSION_FRAME_THRESHOLD = 5  # same function this many times in a row


def classify(report: CrashReport) -> CrashReport:
    """Populate report.classification / confidence / evidence in place,
    and also return it (for chaining)."""
    evidence: List[str] = []

    # Known Function name in Backtrace
    hint = _check_known_functions(report, evidence)
    if hint:
        report.classification, report.classification_confidence = hint
        report.classification_evidence = evidence
        return report

    # Backtrace Shape
    repeat_func, repeat_count = _max_consecutive_repeat(report)
    if repeat_count >= _RECURSION_FRAME_THRESHOLD:
        evidence.append(
            f"Backtrace contains {repeat_count} consecutive frames of "
            f"'{repeat_func}' - classic unbounded-recursion signature."
        )
        report.classification = STACK_OVERFLOW
        report.classification_confidence = min(0.95, 0.5 + 0.05 * repeat_count)
        report.classification_evidence = evidence
        return report

    # Known Text Patterns
    text_hint = _check_text_hints(report, evidence)
    if text_hint:
        report.classification, report.classification_confidence = text_hint
        report.classification_evidence = evidence
        return report

    # Self Deadlock
    if _looks_like_spinlock_self_deadlock(report):
        evidence.append(
            "Multiple stack frames show the same lock-acquire helper "
            "back-to-back with no intervening unlock - looks like a "
            "self-deadlock on a non-recursive lock."
        )
        report.classification = DEADLOCK_OR_HANG
        report.classification_confidence = 0.6
        report.classification_evidence = evidence
        return report

    # Fallback
    evidence.append("No known function name, backtrace shape, or panic "
                     "text pattern matched. Needs manual review.")
    report.classification = UNKNOWN
    report.classification_confidence = 0.0
    report.classification_evidence = evidence
    return report


def _check_known_functions(report: CrashReport, evidence: List[str]) -> Optional[Tuple[str, float]]:
    for frame in report.backtrace:
        if frame.function in _KNOWN_FUNCTION_HINTS:
            category, confidence = _KNOWN_FUNCTION_HINTS[frame.function]
            evidence.append(
                f"Backtrace frame #{frame.index} is '{frame.function}', a "
                f"known {category.replace('_', ' ').lower()} trigger."
            )
            return category, confidence
    return None


def _check_text_hints(report: CrashReport, evidence: List[str]) -> Optional[Tuple[str, float]]:
    haystack = " ".join(filter(None, [report.oops_type, report.panic_message]))
    for marker, category, confidence in _TEXT_HINTS:
        if marker in haystack:
            evidence.append(
                f"Panic/oops text contains '{marker}', matching known "
                f"{category.replace('_', ' ').lower()} pattern."
            )
            return category, confidence
    return None


def _max_consecutive_repeat(report: CrashReport) -> Tuple[Optional[str], int]:
    best_func, best_count = None, 0
    cur_func, cur_count = None, 0
    for frame in report.backtrace:
        if frame.function == cur_func:
            cur_count += 1
        else:
            cur_func, cur_count = frame.function, 1
        if cur_count > best_count:
            best_func, best_count = cur_func, cur_count
    return best_func, best_count


def _looks_like_spinlock_self_deadlock(report: CrashReport) -> bool:
    lock_frame_names = {"spin_lock", "queued_spin_lock_slowpath", "_raw_spin_lock"}
    hits = sum(1 for f in report.backtrace if f.function in lock_frame_names)
    return hits >= 2
