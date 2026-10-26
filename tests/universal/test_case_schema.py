"""Unit tests for FailureCase schema, digest, and serialization."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from universal_harness.case.schema import (
    EnvironmentSpec,
    ExecutionSpec,
    ExpectedOutcomeSpec,
    FailureCase,
    SourceSpec,
)
from universal_harness.case.loader import load_failure_case, save_failure_case


def test_failure_case_creation_and_digest_stability() -> None:
    case1 = FailureCase(
        id="test-case-01",
        name="Test Timeout Scenario",
        source=SourceSpec(system="autter_runtime", reference="commit-abc"),
        environment=EnvironmentSpec(seed=42),
        execution=ExecutionSpec(command="python -m test"),
        perturbations={"timeout_ms": 100},
        expected=ExpectedOutcomeSpec(outcome="failure", exit_code=1),
    )

    case2 = FailureCase(
        id="test-case-01",
        name="Test Timeout Scenario",
        source=SourceSpec(system="autter_runtime", reference="commit-abc"),
        environment=EnvironmentSpec(seed=42),
        execution=ExecutionSpec(command="python -m test"),
        perturbations={"timeout_ms": 100},
        expected=ExpectedOutcomeSpec(outcome="failure", exit_code=1),
    )

    assert case1.digest == case2.digest
    assert len(case1.digest) == 64


def test_empty_id_raises_validation_error() -> None:
    with pytest.raises(Exception):
        FailureCase(
            id="   ",
            name="Blank ID",
            source=SourceSpec(system="local"),
            execution=ExecutionSpec(command="echo 1"),
        )


def test_save_and_load_roundtrip_yaml_and_json(tmp_path: Path) -> None:
    case = FailureCase(
        id="roundtrip-case",
        name="Roundtrip Test",
        source=SourceSpec(system="local_process"),
        execution=ExecutionSpec(command="python --version"),
        perturbations={"flag": True, "count": 10},
    )

    yaml_file = tmp_path / "case.yaml"
    save_failure_case(case, yaml_file, format="yaml")
    loaded_yaml = load_failure_case(yaml_file)
    assert loaded_yaml.id == case.id
    assert loaded_yaml.digest == case.digest

    json_file = tmp_path / "case.json"
    save_failure_case(case, json_file, format="json")
    loaded_json = load_failure_case(json_file)
    assert loaded_json.id == case.id
    assert loaded_json.digest == case.digest
