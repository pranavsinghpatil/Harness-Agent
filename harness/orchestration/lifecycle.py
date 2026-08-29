"""Lifecycle state machine for HarnessEvaluations."""

from __future__ import annotations
from enum import Enum


class EvaluationLifecycleState(str, Enum):
    """Lifecycle state machine states for HarnessEvaluation."""
    INITIALIZED = "INITIALIZED"
    CONFIGURED = "CONFIGURED"
    BASELINE_RUNNING = "BASELINE_RUNNING"
    BASELINE_COMPLETED = "BASELINE_COMPLETED"
    DIAGNOSING = "DIAGNOSING"
    DIAGNOSIS_COMPLETED = "DIAGNOSIS_COMPLETED"
    PATCHING = "PATCHING"
    PATCH_GENERATED = "PATCH_GENERATED"
    VERIFICATION_RUNNING = "VERIFICATION_RUNNING"
    VERIFIED_SAFE = "VERIFIED_SAFE"
    VERIFIED_FAILED = "VERIFIED_FAILED"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
