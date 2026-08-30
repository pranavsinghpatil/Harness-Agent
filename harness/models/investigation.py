"""Structured control-plane artifacts for autonomous investigation lifecycles."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Optional


class InvestigationPhase(str, Enum):
    """Fine-grained phase reported while a session remains active."""

    INVESTIGATING = "INVESTIGATING"
    DIAGNOSING = "DIAGNOSING"
    PATCH_PROPOSED = "PATCH_PROPOSED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    VERIFYING = "VERIFYING"
    REGRESSING = "REGRESSING"
    PATCH_REJECTED = "PATCH_REJECTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class PatchApproval:
    """Human decision artifact binding a reviewer decision to one patch."""

    investigation_id: str
    patch_id: str
    decision: str
    reviewed_by: str
    reason: str = ""
    decided_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the approval artifact for REST, WebSocket, and audit logs."""
        return {
            "investigation_id": self.investigation_id,
            "patch_id": self.patch_id,
            "decision": self.decision,
            "reviewed_by": self.reviewed_by,
            "reason": self.reason,
            "decided_at": self.decided_at,
        }


@dataclass(frozen=True)
class InvestigationConclusion:
    """Evidence-backed final conclusion for one autonomous investigation."""

    outcome: str
    leading_hypothesis: Optional[dict[str, Any]] = None
    failure_boundary: Optional[dict[str, Any]] = None
    causal_chain: list[dict[str, Any]] = field(default_factory=list)
    counterexample: Optional[dict[str, Any]] = None
    proposed_patch: Optional[dict[str, Any]] = None
    approval: Optional[dict[str, Any]] = None
    verification: Optional[dict[str, Any]] = None
    regression: list[dict[str, Any]] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    completed_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the conclusion as a stable frontend and agent contract."""
        return {
            "outcome": self.outcome,
            "leading_hypothesis": self.leading_hypothesis,
            "failure_boundary": self.failure_boundary,
            "causal_chain": self.causal_chain,
            "counterexample": self.counterexample,
            "proposed_patch": self.proposed_patch,
            "approval": self.approval,
            "verification": self.verification,
            "regression": self.regression,
            "limitations": self.limitations,
            "completed_at": self.completed_at,
        }
