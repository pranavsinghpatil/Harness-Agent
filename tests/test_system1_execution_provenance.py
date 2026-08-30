"""Tests for scheduler-governed System 1 execution provenance."""

from __future__ import annotations

from typing import Any

from sandbox.actuators.command import ActuatorCommand
from sandbox.actuators.pipeline import ActuatorPipeline
from sandbox.api.environment import SandboxEnvironment
from sandbox.api.tools import get_scenario
from scenarios.schema import ScenarioDefinition


def test_controller_execution_is_timestamped_through_scheduler_and_actuator() -> None:
    scenario: ScenarioDefinition | None = get_scenario("showcase_normal_baseline")
    assert scenario is not None
    events: list[tuple[str, str, str, dict[str, Any]]] = []

    def capture(source: str, event_type: str, severity: str, payload: dict[str, Any]) -> None:
        events.append((source, event_type, severity, payload))

    environment: SandboxEnvironment = SandboxEnvironment(scenario=scenario, event_listener=capture)
    environment.reset()
    for _ in range(8):
        environment.step(0.01)

    event_types: list[str] = [event_type for _, event_type, _, _ in events]
    assert "SENSOR_SAMPLED" in event_types
    assert "PACKET_DELIVERED" in event_types
    assert "TASK_SCHEDULED" in event_types
    assert "COMPUTE_STARTED" in event_types
    assert "TASK_COMPLETED" in event_types
    assert "COMMAND_ISSUED" in event_types
    assert "ACTUATOR_APPLIED" in event_types

    command_payload: dict[str, Any] = next(
        payload for _, event_type, _, payload in events if event_type == "COMMAND_ISSUED"
    )
    assert command_payload["compute_started_at"] <= command_payload["compute_completed_at"]
    assert command_payload["compute_completed_at"] <= command_payload["input_timestamp"] + 0.02
    assert "observation_id" in command_payload
    assert "observation_age_s" in command_payload

    scheduled_controller: dict[str, Any] = next(
        payload
        for _, event_type, _, payload in events
        if event_type == "TASK_SCHEDULED" and payload["name"] == "controller"
    )
    completed_controller: dict[str, Any] = next(
        payload
        for _, event_type, _, payload in events
        if event_type == "TASK_COMPLETED" and payload["name"] == "controller"
    )
    assert scheduled_controller["timestamp"] <= completed_controller["completed_at"]


def test_missing_observation_reports_absent_age() -> None:
    scenario: ScenarioDefinition | None = get_scenario("showcase_normal_baseline")
    assert scenario is not None
    events: list[tuple[str, str, str, dict[str, Any]]] = []

    def capture(source: str, event_type: str, severity: str, payload: dict[str, Any]) -> None:
        events.append((source, event_type, severity, payload))

    environment: SandboxEnvironment = SandboxEnvironment(scenario=scenario, event_listener=capture)
    environment.reset()
    environment.step(0.01)
    first_cmd: dict[str, Any] = next(
        payload for _, event_type, _, payload in events if event_type == "COMMAND_ISSUED"
    )
    assert first_cmd["observation_id"] is None
    assert first_cmd["observation_age_s"] is None


def test_perception_is_not_available_before_compute_completion() -> None:
    scenario: ScenarioDefinition | None = get_scenario("showcase_normal_baseline")
    assert scenario is not None
    events: list[tuple[str, str, str, dict[str, Any]]] = []

    def capture(source: str, event_type: str, severity: str, payload: dict[str, Any]) -> None:
        events.append((source, event_type, severity, payload))

    environment: SandboxEnvironment = SandboxEnvironment(scenario=scenario, event_listener=capture)
    environment.hardware.profile.cpu_capacity_units_per_sec = 2.5
    environment.reset()
    for _ in range(8):
        environment.step(0.05)

    completed: dict[str, dict[str, Any]] = {
        payload["task_id"]: payload
        for _, event_type, _, payload in events
        if event_type == "TASK_COMPLETED" and payload["name"] == "perception"
    }
    available: list[dict[str, Any]] = [
        payload for _, event_type, _, payload in events if event_type == "OBSERVATION_AVAILABLE"
    ]
    assert available
    for observation in available:
        task: dict[str, Any] = completed[observation["observation_id"]]
        assert observation["available_at"] == task["completed_at"]
        assert observation["available_at"] >= task["input_timestamp"]


def test_actuator_application_provenance_reports_effective_command() -> None:
    pipeline: ActuatorPipeline = ActuatorPipeline(base_delay_s=0.001, jitter_std_s=0.0)
    command: ActuatorCommand = ActuatorCommand(
        throttle=1.0,
        brake=0.8,
        steering=0.25,
        emergency_stop=True,
    )
    assert pipeline.submit_command(command, 0.0) is True
    pipeline.throttle_effectiveness_factor = 0.5
    pipeline.brake_effectiveness_factor = 0.25
    pipeline.stuck_steering_angle = -0.5

    effective: ActuatorCommand = pipeline.step(0.01)
    applied: ActuatorCommand = pipeline.applied_commands_this_step[0]

    assert applied.command_id == effective.command_id
    assert applied.throttle == 0.5
    assert applied.brake == 0.2
    assert applied.steering == -0.5
    assert applied.emergency_stop is True
