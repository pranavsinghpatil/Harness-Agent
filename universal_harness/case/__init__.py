"""Case contracts and serialization."""

from universal_harness.case.schema import (
    FailureCase,
    SourceSpec,
    EnvironmentSpec,
    ExecutionSpec,
    ExpectedOutcomeSpec,
)
from universal_harness.case.loader import load_failure_case, save_failure_case

__all__ = [
    "FailureCase",
    "SourceSpec",
    "EnvironmentSpec",
    "ExecutionSpec",
    "ExpectedOutcomeSpec",
    "load_failure_case",
    "save_failure_case",
]
