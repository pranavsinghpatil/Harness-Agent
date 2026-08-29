"""Data structures representing code hardening results, diffs, provenance contracts, and validation status."""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import hashlib
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
    RUNTIME_GUARD_WRAPPER = "RUNTIME_GUARD_WRAPPER"
    LLM_SYNTHESIZED = "LLM_SYNTHESIZED"


class PatchValidationStatus(str, Enum):
    """Validation status for synthesized code patches."""
    PENDING = "PENDING"
    SYNTAX_VALID = "SYNTAX_VALID"
    INTERFACE_COMPLIANT = "INTERFACE_COMPLIANT"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    INTERFACE_VIOLATION = "INTERFACE_VIOLATION"
    PATCH_NOT_APPLICABLE = "PATCH_NOT_APPLICABLE"


@dataclass
class PatchProvenance:
    """Rigorous audit trail explaining why, how, and with what evidence code was transformed.

    Attributes:
        source_controller_hash: SHA-256 hash of the input controller source code.
        diagnostic_report_id: Diagnostic report identifier motivating the patch.
        evidence_event_ids: Trace event IDs proving the underlying vulnerability.
        strategy: Primary strategy employed for the code transformation.
        transformations_applied: Ordered list of structural/AST modifications executed.
        rationale: Explanatory summary of why this specific patch fixes the failure.
    """
    source_controller_hash: str
    diagnostic_report_id: str
    evidence_event_ids: List[str] = field(default_factory=list)
    strategy: PatchStrategyType = PatchStrategyType.COMBINED_FAILSAFE_HARDENING
    transformations_applied: List[str] = field(default_factory=list)
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize provenance to dictionary."""
        return {
            "source_controller_hash": self.source_controller_hash,
            "diagnostic_report_id": self.diagnostic_report_id,
            "evidence_event_ids": self.evidence_event_ids,
            "strategy": self.strategy.value if isinstance(self.strategy, Enum) else str(self.strategy),
            "transformations_applied": self.transformations_applied,
            "rationale": self.rationale,
        }


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
        provenance: Detailed provenance contract for developer auditability.
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
    provenance: Optional[PatchProvenance] = None
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
            "provenance": self.provenance.to_dict() if self.provenance else None,
            "metadata": self.metadata,
        }
