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


def emit_autter_telemetry(
    case: FailureCase,
    ingest_key: str | None = None,
    endpoint: str | None = None,
) -> Dict[str, Any]:
    """Emit a reproduced FailureCase as an OpenTelemetry error incident to Autter Runtime."""
    import os
    import urllib.request
    import urllib.error

    from datetime import datetime, timezone
    import uuid

    key = (
        ingest_key
        or os.environ.get("AUTTER_INGEST_KEY")
        or "autter_rt_64a43069290be1d21d382ce68dcdc4c9a72dc140fa2027bb"
    )
    base_url = endpoint or os.environ.get("AUTTER_INGEST_ENDPOINT") or "https://otlp.autter.dev/v1/traces"
    
    # Autter /v1/browser ingester accepts key via query parameter
    url = f"{base_url}?key={key}" if "?key=" not in base_url else base_url

    err_msg = case.expected.error_match or "RuntimeException in reproduced FailureCase"
    stack_trace = f"Error: {err_msg}\n  at executeSandbox (sandbox.py:65)\n  at runFailureCase ({case.id}:1)"

    trace_id = uuid.uuid4().hex
    span_id = uuid.uuid4().hex[:16]
    start_time_ns = int(datetime.now(timezone.utc).timestamp() * 1e9)
    end_time_ns = start_time_ns + int(120 * 1e6)  # ~120ms duration

    payload = {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": case.source.metadata.get("service", "harness-service")}},
                        {"key": "harness.case_id", "value": {"stringValue": case.id}},
                        {"key": "harness.digest", "value": {"stringValue": case.digest}},
                        {"key": "harness.source", "value": {"stringValue": case.source.system}},
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {"name": "universal-harness", "version": "0.2.0"},
                        "spans": [
                            {
                                "traceId": trace_id,
                                "spanId": span_id,
                                "name": f"failure_reproduction:{case.id}",
                                "kind": 1,
                                "startTimeUnixNano": str(start_time_ns),
                                "endTimeUnixNano": str(end_time_ns),
                                "status": {
                                    "code": 2,  # STATUS_CODE_ERROR in OTel
                                    "message": err_msg,
                                },
                                "attributes": [
                                    {"key": "exception.type", "value": {"stringValue": case.expected.error_match or "RuntimeException"}},
                                    {"key": "exception.message", "value": {"stringValue": err_msg}},
                                    {"key": "exception.stacktrace", "value": {"stringValue": stack_trace}},
                                    {"key": "harness.reproduced", "value": {"boolValue": True}},
                                    {"key": "harness.seed", "value": {"intValue": case.environment.seed}},
                                ],
                            }
                        ],
                    }
                ],
            }
        ]
    }

    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "x-autter-key": key,
            "User-Agent": "universal-harness/0.2.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return {
                "status_code": resp.status,
                "success": True,
                "endpoint": url,
                "incident_id": case.id,
            }
    except urllib.error.HTTPError as exc:
        return {
            "status_code": exc.code,
            "success": False,
            "error": str(exc),
            "endpoint": url,
            "incident_id": case.id,
        }
    except Exception as exc:
        return {
            "status_code": 0,
            "success": False,
            "error": str(exc),
            "endpoint": url,
            "incident_id": case.id,
        }
