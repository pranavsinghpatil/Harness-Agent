"""Backend contract test for the complete System 2 -> System 1 loop."""

from __future__ import annotations

from typing import Any

from backend.server import app
from fastapi.testclient import TestClient
from httpx import Response
from starlette.testclient import WebSocketTestSession


def _first_index(
    events: list[dict[str, Any]], event_type: str, name: str | None = None
) -> int:
    index: int
    event: dict[str, Any]
    for index, event in enumerate(events):
        if event["type"] != event_type:
            continue
        if name is not None and event.get("payload", {}).get("name") != name:
            continue
        return index
    raise AssertionError(f"missing event {event_type!r} with name {name!r}")


def _create_investigation(client: TestClient) -> tuple[str, Response]:
    """Create a short investigation through the public REST endpoint."""
    response: Response = client.post(
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
    body: dict[str, Any] = response.json()
    return str(body["investigation_id"]), response


def _collect_stream(client: TestClient, investigation_id: str) -> list[dict[str, Any]]:
    """Collect replayed and live WebSocket events through investigation completion."""
    events: list[dict[str, Any]] = []
    terminal_types: set[str] = {"INVESTIGATION_COMPLETED", "INVESTIGATION_FAILED"}
    websocket: WebSocketTestSession
    with client.websocket_connect(
        f"/ws/investigations/{investigation_id}"
    ) as websocket:
        event: dict[str, Any]
        while True:
            event = websocket.receive_json()
            events.append(event)
            if event["type"] in terminal_types:
                break
    return events


def _assert_event_types(events: list[dict[str, Any]]) -> None:
    """Require the observable planning, execution, evidence, and decision stages."""
    event: dict[str, Any]
    event_types: set[str] = {event["type"] for event in events}
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


def _assert_experiment_order(events: list[dict[str, Any]]) -> None:
    """Validate one experiment's scheduler and actuation relationships."""
    event: dict[str, Any]
    started_events: list[dict[str, Any]] = [
        event for event in events if event["type"] == "EXPERIMENT_STARTED"
    ]
    experiment_id: str = str(started_events[0]["experiment_id"])
    experiment_events: list[dict[str, Any]] = [
        event for event in events if event.get("experiment_id") == experiment_id
    ]
    experiment_started: int = _first_index(experiment_events, "EXPERIMENT_STARTED")
    perception_scheduled: int = _first_index(
        experiment_events, "PERCEPTION_TASK_SCHEDULED"
    )
    perception_started: int = _first_index(
        experiment_events, "COMPUTE_STARTED", name="perception"
    )
    observation_available: int = _first_index(
        experiment_events, "OBSERVATION_AVAILABLE"
    )
    controller_scheduled: int = _first_index(
        experiment_events, "CONTROLLER_TASK_SCHEDULED"
    )
    controller_started: int = _first_index(
        experiment_events, "COMPUTE_STARTED", name="controller"
    )
    command_issued: int = _first_index(experiment_events, "COMMAND_ISSUED")
    actuator_applied: int = _first_index(experiment_events, "ACTUATOR_APPLIED")
    experiment_completed: int = _first_index(
        experiment_events, "EXPERIMENT_COMPLETED"
    )

    assert experiment_started < perception_scheduled < perception_started
    assert perception_started < observation_available < experiment_completed
    assert controller_scheduled < command_issued
    assert controller_started < command_issued
    assert command_issued < actuator_applied < experiment_completed


def _assert_provenance(events: list[dict[str, Any]], investigation_id: str) -> None:
    """Ensure execution events retain every identity needed for evidence tracing."""
    assert len({event["event_id"] for event in events}) == len(events)
    assert all(event["investigation_id"] == investigation_id for event in events)
    system1_types: set[str] = {
        "PERCEPTION_TASK_SCHEDULED",
        "OBSERVATION_AVAILABLE",
        "CONTROLLER_TASK_SCHEDULED",
        "COMMAND_ISSUED",
        "ACTUATOR_APPLIED",
    }
    experiment_lifecycle_types: set[str] = {
        "EXPERIMENT_PLANNED",
        "EXPERIMENT_STARTED",
        "EXPERIMENT_COMPLETED",
    }
    event: dict[str, Any]
    for event in events:
        if event["type"] in system1_types or event["type"] in experiment_lifecycle_types:
            assert event.get("experiment_id")
            assert event.get("evaluation_id")
        if event["type"] in experiment_lifecycle_types:
            assert event.get("run_id")
            assert event.get("episode_id")
        if event["type"] in system1_types:
            assert event.get("run_id")
            assert event.get("episode_id")


def _assert_history_matches_stream(
    client: TestClient, investigation_id: str, events: list[dict[str, Any]]
) -> None:
    """Verify polling exposes exactly the same ordered history as WebSocket replay."""
    listed_events: Response = client.get(
        f"/api/harness/investigations/{investigation_id}/events"
    )
    assert listed_events.status_code == 200
    assert listed_events.json() == events


def test_investigation_api_streams_complete_provenance_loop() -> None:
    """Validate asynchronous creation, live execution, evidence, and terminal state."""
    client: TestClient = TestClient(app)
    investigation_id: str
    creation_response: Response
    investigation_id, creation_response = _create_investigation(client)
    assert creation_response.json()["status"] in {"CREATED", "RUNNING", "COMPLETED"}

    events: list[dict[str, Any]] = _collect_stream(client, investigation_id)
    assert events[-1]["type"] == "INVESTIGATION_COMPLETED"
    _assert_event_types(events)
    _assert_experiment_order(events)
    _assert_provenance(events, investigation_id)

    status_response: Response = client.get(
        f"/api/harness/investigations/{investigation_id}"
    )
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "COMPLETED"
    _assert_history_matches_stream(client, investigation_id, events)
