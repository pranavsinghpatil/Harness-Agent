"""Tests for isolated process runner and deterministic replayer."""

from __future__ import annotations

from pathlib import Path
from universal_harness.case.schema import (
    EnvironmentSpec,
    ExecutionSpec,
    ExpectedOutcomeSpec,
    FailureCase,
    SourceSpec,
)
from universal_harness.replay.replayer import DeterministicReplayer
from universal_harness.runner.sandbox import ExecutionSandbox


def test_sandbox_executes_process_and_captures_failure() -> None:
    case = FailureCase(
        id="sandbox-test",
        name="Sandbox Subprocess Test",
        source=SourceSpec(system="test"),
        execution=ExecutionSpec(command="python -m examples.fixtures.payment_service"),
        perturbations={"discount_path": True, "cart_total_present": False},
        expected=ExpectedOutcomeSpec(outcome="failure", error_match="TypeError: Cannot read properties"),
    )

    sandbox = ExecutionSandbox()
    result = sandbox.run(case)

    assert result.outcome == "failure"
    assert result.exit_code == 1
    assert result.matched_error is True
    assert "TypeError: Cannot read properties" in result.stderr
    assert len(result.trace_hash) == 64


def test_deterministic_replayer_produces_consistent_hashes() -> None:
    case = FailureCase(
        id="deterministic-replayer-test",
        name="Deterministic Replay Test",
        source=SourceSpec(system="test"),
        execution=ExecutionSpec(command="python -m examples.fixtures.payment_service"),
        perturbations={"discount_path": True, "cart_total_present": False},
        expected=ExpectedOutcomeSpec(outcome="failure", error_match="TypeError"),
    )

    replayer = DeterministicReplayer()
    report = replayer.replay(case, trials=3, vary_seeds=False)

    assert report.trials_count == 3
    assert report.reproduced_count == 3
    assert report.reproduction_rate == 1.0
    assert report.is_deterministic is True
    assert report.verdict == "deterministic_reproduction"
    assert len(report.trials) == 3
