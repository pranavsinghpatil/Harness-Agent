"""Safety properties and invariant definitions evaluated against ground truth."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from enum import Enum


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    FATAL = "fatal"


@dataclass
class SafetyViolation:
    rule_name: str
    timestamp: float
    severity: Severity
    description: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "timestamp": round(self.timestamp, 4),
            "severity": self.severity.value,
            "description": self.description,
            "details": self.details,
        }
