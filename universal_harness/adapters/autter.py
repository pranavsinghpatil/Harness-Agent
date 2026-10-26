"""Autter Runtime telemetry and incident adapter.

Ingests OpenTelemetry exception payloads and incident reports captured by
Autter Runtime (@autter/runtime-node, @autter/runtime-browser) and converts them
into deterministic, reproducible FailureCase specifications.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Union
from universal_harness.case.schema import (
    EnvironmentSpec,
    ExecutionSpec,
    ExpectedOutcomeSpec,
    FailureCase,
    SourceSpec,
)


def import_autter_incident(
    incident_data: Union[str, Path, Dict[str, Any]],
    reproduce_command: str = "python -m examples.fixtures.autter_service_mock",
) -> FailureCase:
    """Transform an Autter Runtime incident JSON payload into a universal FailureCase."""
    if isinstance(incident_data, (str, Path)) and Path(str(incident_data)).exists():
        raw_text = Path(str(incident_data)).read_text(encoding="utf-8")
        payload = json.loads(raw_text)
    elif isinstance(incident_data, str):
        payload = json.loads(incident_data)
    else:
        payload = dict(incident_data)

    incident_id = str(payload.get("incident_id") or payload.get("id") or "autter-inc-unknown")
    service_name = str(payload.get("service") or payload.get("service_name") or "backend-service")
    commit_sha = payload.get("commit") or payload.get("git_sha")
    error_obj = payload.get("error", {})
    error_type = error_obj.get("type", "Error")
    error_msg = error_obj.get("message", "Unhandled runtime error")
    telemetry_attrs = payload.get("telemetry_attributes") or payload.get("attributes") or {}

    # Extract perturbations from telemetry context
    perturbations: Dict[str, Any] = {}
    for k, v in telemetry_attrs.items():
        # Clean parameter key
        clean_key = k.replace(".", "_").replace("-", "_")
        perturbations[clean_key] = v

    # If timeout or latency exists in payload top-level
    if "latency_ms" in payload:
        perturbations["latency_ms"] = payload["latency_ms"]
    if "timeout_ms" in payload:
        perturbations["timeout_ms"] = payload["timeout_ms"]

    case = FailureCase(
        id=f"autter-{incident_id.lower().replace('_', '-')}",
        name=f"Autter Incident: {error_type} in {service_name}",
        description=f"Auto-generated failure case from Autter Runtime telemetry for {service_name} at commit {commit_sha or 'HEAD'}.",
        source=SourceSpec(
            system="autter_runtime",
            reference=commit_sha,
            metadata={
                "incident_id": incident_id,
                "service": service_name,
                "stack_trace": error_obj.get("stack"),
            },
        ),
        environment=EnvironmentSpec(
            seed=42,
            env_vars={"AUTTER_INCIDENT_ID": incident_id, "SERVICE_NAME": service_name},
            runtime="node/python",
        ),
        execution=ExecutionSpec(
            command=reproduce_command,
            timeout_seconds=20.0,
            input_payload=payload.get("request") or payload.get("input_payload"),
        ),
        perturbations=perturbations,
        expected=ExpectedOutcomeSpec(
            outcome="failure",
            exit_code=1,
            error_match=error_msg or error_type,
        ),
        observed={
            "error_type": error_type,
            "error_message": error_msg,
            "occurrences": payload.get("occurrences", 1),
            "trace_id": payload.get("trace_id"),
        },
        tags=["autter", "runtime", "telemetry", service_name],
    )
    return case
