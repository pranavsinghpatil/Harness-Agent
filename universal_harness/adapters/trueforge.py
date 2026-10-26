"""TrueForge simulation fault adapter."""

from __future__ import annotations

from typing import Any, Dict
from universal_harness.case.schema import (
    EnvironmentSpec,
    ExecutionSpec,
    ExpectedOutcomeSpec,
    FailureCase,
    SourceSpec,
)


def import_trueforge_fault_spec(
    scenario_name: str,
    faults: Dict[str, Any],
    seed: int = 42,
    command: str = "python -m examples.fixtures.robot_nav_sim",
) -> FailureCase:
    """Convert TrueForge hardware simulation fault injections into a universal FailureCase."""
    return FailureCase(
        id=f"trueforge-{scenario_name.lower().replace('_', '-')}",
        name=f"TrueForge Sandbox: {scenario_name}",
        description="Hardware-semantic fault injection case imported from TrueForge SIL sandbox",
        source=SourceSpec(
            system="trueforge_sandbox",
            reference=f"seed-{seed}",
            metadata={"scenario": scenario_name},
        ),
        environment=EnvironmentSpec(
            seed=seed,
            runtime="python3.11",
        ),
        execution=ExecutionSpec(
            command=command,
            timeout_seconds=15.0,
        ),
        perturbations=faults,
        expected=ExpectedOutcomeSpec(
            outcome="failure",
            exit_code=1,
            error_match="CollisionBreach|SafetyViolation",
        ),
        tags=["trueforge", "robotics", "fault_injection"],
    )
