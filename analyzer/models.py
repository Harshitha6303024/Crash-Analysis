"""shared data model produced by every analyzer engine and
consumed by the classifier and report generator.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class StackFrame:
    """One frame of a kernel backtrace."""
    index: int
    function: str
    offset: Optional[str] = None    
    module: Optional[str] = None    
    address: Optional[str] = None   

    def __str__(self) -> str:
        loc = f"{self.function}{self.offset or ''}"
        if self.module:
            loc += f" [{self.module}]"
        return f"#{self.index:<2} {loc}"


@dataclass
class CrashReport:
    """Everything extracted from one crash dump, plus the classifier's
    verdict once classify() has been run on it.
    """
    vmcore_path: str
    vmlinux_path: Optional[str] = None
    engine: str = "unknown"               

    crash_time: Optional[str] = None
    panic_message: Optional[str] = None
    oops_type: Optional[str] = None      
    cpu: Optional[int] = None
    comm: Optional[str] = None            
    pid: Optional[int] = None

    backtrace: List[StackFrame] = field(default_factory=list)
    modules_loaded: List[str] = field(default_factory=list)


    classification: Optional[str] = None
    classification_confidence: Optional[float] = None
    classification_evidence: List[str] = field(default_factory=list)

    @property
    def faulting_function(self) -> Optional[str]:
        """The innermost (deepest) frame, i.e. where the fault occurred."""
        return self.backtrace[0].function if self.backtrace else None
