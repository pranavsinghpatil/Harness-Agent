"""Data structures representing code hardening results, diffs, and validation status."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
import time


class PatchStrategyType(str, Enum):
    """Available deterministic and dynamic patch strategies."""
    DYNAMIC_STOPPING_BUFFER = "DYNAMIC_STOPPING_BUFFER"
    STALE_SENSOR_FAIL_SAFE = "STALE_SENSOR_FAIL_SAFE"
    SENSOR_FUSION_REDUNDANCY = "SENSOR_FUSION_REDUNDANCY"
    HARDWARE_DELAY_COMPENSATION = "HARDWARE_DELAY_COMPENSATION"
    COMBINED_FAILSAFE_HARDENING = "COMBINED_FAILSAFE_HARDENING"
    LLM_SYNTHESIZED = "LLM_SYNTHESIZED"


class PatchValidationStatus(str, Enum):
    """Validation status for synthesized code patches."""
    PENDING = "PENDING"
    SYNTAX_VALID = "SYNTAX_VALID"
    INTERFACE_COMPLIANT = "INTERFACE_COMPLIANT"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    INTERFACE_VIOLATION = "INTERFACE_VIOLATION"


@dataclass
class PatchResult:
    """Result of an autonomous code patching operation.

    Attributes:
        patch_id: Unique patch identifier.
        report_id: Associated diagnostic report ID.
        strategies_applied: List of strategy names applied.
        original_code: Pre-patch controller source code.
        patched_code: Post-patch hardened controller source code.
        unified_diff: Standard unified diff showing exact modifications.
        validation_status: AST / syntax validation status.
        validation_message: Explanation of validation errors if any.
        created_at: Patch generation timestamp.
        metadata: Strategy-specific parameters or AST transform metadata.
    """
    patch_id: str = field(default_factory=lambda: f"patch_{uuid.uuid4().hex[:8]}")
    report_id: str = ""
    strategies_applied: List[PatchStrategyType] = field(default_factory=list)
    original_code: str = ""
    patched_code: str = ""
    unified_diff: str = ""
    validation_status: PatchValidationStatus = PatchValidationStatus.PENDING
    validation_message: str = "Validation successful"
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize patch result to dictionary."""
        return {
            "patch_id": self.patch_id,
            "report_id": self.report_id,
            "strategies_applied": [
                s.value if isinstance(s, Enum) else str(s) for s in self.strategies_applied
            ],
            "original_code": self.original_code,
            "patched_code": self.patched_code,
            "unified_diff": self.unified_diff,
            "validation_status": self.validation_status.value if isinstance(self.validation_status, Enum) else str(self.validation_status),
            "validation_message": self.validation_message,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }
