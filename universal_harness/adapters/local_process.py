"""Local process and command adapter."""

from __future__ import annotations

from typing import Any, Dict, Optional
from universal_harness.case.schema import (
    EnvironmentSpec,
    ExecutionSpec,
    ExpectedOutcomeSpec,
    FailureCase,
    SourceSpec,
)


def create_local_failure_case(
    case_id: str,
    command: str,
    perturbations: Optional[Dict[str, Any]] = None,
    error_match: Optional[str] = None,
    timeout_seconds: float = 30.0,
    seed: int = 42,
) -> FailureCase:
    """Create a FailureCase for any local script or CLI command."""
    return FailureCase(
        id=case_id,
        name=f"Local Process: {case_id}",
        source=SourceSpec(system="local_process"),
        environment=EnvironmentSpec(seed=seed),
        execution=ExecutionSpec(command=command, timeout_seconds=timeout_seconds),
        perturbations=perturbations or {},
        expected=ExpectedOutcomeSpec(outcome="failure", error_match=error_match),
        tags=["local", "cli"],
    )
