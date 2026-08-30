"""Backend contract test for the complete System 2 -> System 1 loop."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from backend.server import app


def _first_index(
    events: list[dict[str, Any]], event_type: str, name: str | None = None
) -> int:
    for index, event in enumerate(events):
        if event["type"] != event_type:
            continue
        if name is not None and event.get("payload", {}).get("name") != name:
            continue
        return index
    raise AssertionError(f"missing event {event_type!r} with name {name!r}")


def test_investigation_api_streams_complete_provenance_loop() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/harness/investigations",
        json={
            "objective": "Validate the complete autonomous investigation loop.",
            "scenario_id": "showcase_normal_baseline",
            "hardware_preset_id": "RDK_X5",
            "seed": 1337,
            "budget": 2,
            "max_boundary_steps": 0,
            "max_sim_time": 0.2,
        },
    )

    assert response.status_code == 202
    investigation_id = response.json()["investigation_id"]
    events: list[dict[str, Any]] = []

    with client.websocket_connect(f"/ws/investigations/{investigation_id}") as websocket:
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["type"] in {"INVESTIGATION_COMPLETED", "INVESTIGATION_FAILED"}:
                break

    assert events[-1]["type"] == "INVESTIGATION_COMPLETED"
    event_types = {event["type"] for event in events}
    assert {
        "EXPERIMENT_STARTED",
        "PERCEPTION_TASK_SCHEDULED",
        "OBSERVATION_AVAILABLE",
        "CONTROLLER_TASK_SCHEDULED",
        "COMMAND_ISSUED",
        "ACTUATOR_APPLIED",
        "EXPERIMENT_COMPLETED",
        "EVIDENCE_CAPTURED",
        "HYPOTHESIS_UPDATED",
        "DECISION_RECORDED",
        "NEXT_EXPERIMENT_SELECTED",
    }.issubset(event_types)

    experiment_id = next(
        event["experiment_id"]
        for event in events
        if event["type"] == "EXPERIMENT_STARTED"
    )
    experiment_events = [
        event for event in events if event["experiment_id"] == experiment_id
    ]
    experiment_started = _first_index(experiment_events, "EXPERIMENT_STARTED")
    perception_scheduled = _first_index(experiment_events, "PERCEPTION_TASK_SCHEDULED")
    perception_started = _first_index(
        experiment_events, "COMPUTE_STARTED", name="perception"
    )
    observation_available = _first_index(experiment_events, "OBSERVATION_AVAILABLE")
    controller_scheduled = _first_index(
        experiment_events, "CONTROLLER_TASK_SCHEDULED"
    )
    controller_started = _first_index(
        experiment_events, "COMPUTE_STARTED", name="controller"
    )
    command_issued = _first_index(experiment_events, "COMMAND_ISSUED")
    actuator_applied = _first_index(experiment_events, "ACTUATOR_APPLIED")
    experiment_completed = _first_index(experiment_events, "EXPERIMENT_COMPLETED")

    assert experiment_started < perception_scheduled < perception_started
    assert perception_started < observation_available < experiment_completed
    assert controller_scheduled < command_issued
    assert controller_started < command_issued
    assert command_issued < actuator_applied < experiment_completed

    invariant_indexes = [
        index
        for index, event in enumerate(events)
        if event["type"] == "INVARIANT_BREACHED"
    ]
    if invariant_indexes:
        assert invariant_indexes[0] > _first_index(events, "ACTUATOR_APPLIED")

    assert len({event["event_id"] for event in events}) == len(events)
    assert all(event["investigation_id"] == investigation_id for event in events)

    system1_types = {
        "PERCEPTION_TASK_SCHEDULED",
        "OBSERVATION_AVAILABLE",
        "CONTROLLER_TASK_SCHEDULED",
        "COMMAND_ISSUED",
        "ACTUATOR_APPLIED",
    }
    for event in events:
        if event["type"] in system1_types:
            assert event["experiment_id"]
            assert event["evaluation_id"]
            assert event["run_id"]
            assert event["episode_id"]

    listed_events = client.get(
        f"/api/harness/investigations/{investigation_id}/events"
    )
    assert listed_events.status_code == 200
    assert listed_events.json() == events
