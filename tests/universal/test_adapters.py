"""Tests for external telemetry adapters."""

from __future__ import annotations

import json
from pathlib import Path
from universal_harness.adapters.autter import import_autter_incident
from universal_harness.adapters.trueforge import import_trueforge_fault_spec


def test_autter_runtime_adapter_ingestion() -> None:
    incident_payload = {
        "incident_id": "inc-checkout-991",
        "service": "checkout-api",
        "commit": "a3b91c0",
        "occurrences": 85,
        "error": {
            "type": "TransactionTimeoutError",
            "message": "Gateway call timed out",
            "stack": "Error: Gateway call timed out\n  at callGateway()",
        },
        "telemetry_attributes": {
            "latency_ms": 320,
            "db.pool.busy": True,
        },
    }

    case = import_autter_incident(incident_payload)

    assert case.id == "autter-inc-checkout-991"
    assert case.source.system == "autter_runtime"
    assert case.source.reference == "a3b91c0"
    assert case.perturbations["latency_ms"] == 320
    assert case.perturbations["db_pool_busy"] is True
    assert case.expected.error_match == "Gateway call timed out"
    assert case.expected.outcome == "failure"


def test_trueforge_adapter_ingestion() -> None:
    faults = {"sensor_staleness": 200, "brake_delay": 150}
    case = import_trueforge_fault_spec(
        scenario_name="CollisionRisk",
        faults=faults,
        seed=101,
    )

    assert case.id == "trueforge-collisionrisk"
    assert case.source.system == "trueforge_sandbox"
    assert case.environment.seed == 101
    assert case.perturbations["sensor_staleness"] == 200
    assert case.expected.outcome == "failure"
