"""Adapters for ingesting external telemetry into FailureCases."""

from universal_harness.adapters.autter import import_autter_incident
from universal_harness.adapters.trueforge import import_trueforge_fault_spec
from universal_harness.adapters.local_process import create_local_failure_case

__all__ = [
    "import_autter_incident",
    "import_trueforge_fault_spec",
    "create_local_failure_case",
]
