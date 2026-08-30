"""Tests for scheduler-governed System 1 execution provenance."""

from __future__ import annotations

from typing import Any

from sandbox.api.environment import SandboxEnvironment
from sandbox.api.tools import get_scenario


def test_controller_execution_is_timestamped_through_scheduler_and_actuator() -> None:
    scenario = get_scenario("showcase_normal_baseline")
    assert scenario is not None
    events: list[tuple[str, str, str, dict[str, Any]]] = []

    def capture(source: str, event_type: str, severity: str, payload: dict[str, Any]) -> None:
        events.append((source, event_type, severity, payload))

    environment = SandboxEnvironment(scenario=scenario, event_listener=capture)
    environment.reset()
    for _ in range(8):
        environment.step(0.01)

    event_types = [event_type for _, event_type, _, _ in events]
    assert "SENSOR_SAMPLED" in event_types
    assert "PACKET_DELIVERED" in event_types
    assert "TASK_SCHEDULED" in event_types
    assert "COMPUTE_STARTED" in event_types
    assert "TASK_COMPLETED" in event_types
    assert "COMMAND_ISSUED" in event_types
    assert "ACTUATOR_APPLIED" in event_types

    command_payload = next(
        payload for _, event_type, _, payload in events if event_type == "COMMAND_ISSUED"
    )
    assert command_payload["compute_started_at"] <= command_payload["compute_completed_at"]
    assert command_payload["compute_completed_at"] <= command_payload["input_timestamp"] + 0.01

    scheduled_controller = next(
        payload
        for _, event_type, _, payload in events
        if event_type == "TASK_SCHEDULED" and payload["name"] == "controller"
    )
    completed_controller = next(
        payload
        for _, event_type, _, payload in events
        if event_type == "TASK_COMPLETED" and payload["name"] == "controller"
    )
    assert scheduled_controller["timestamp"] <= completed_controller["completed_at"]
