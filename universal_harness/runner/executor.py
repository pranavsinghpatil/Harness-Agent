"""Execution runner and result container."""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import time
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ExecutionResult:
    """Immutable result of a single command execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_ms: float
    timed_out: bool
    matched_error: bool
    outcome: str
    trace_hash: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_ms": round(self.duration_ms, 2),
            "timed_out": self.timed_out,
            "matched_error": self.matched_error,
            "outcome": self.outcome,
            "trace_hash": self.trace_hash,
            "metadata": self.metadata,
        }


def compute_trace_hash(exit_code: int, stdout: str, stderr: str, seed: int) -> str:
    """Compute a deterministic hash representing the observed process behavior."""
    content = f"code:{exit_code}\nstdout:{stdout.strip()}\nstderr:{stderr.strip()}\nseed:{seed}"
    return sha256(content.encode("utf-8")).hexdigest()
