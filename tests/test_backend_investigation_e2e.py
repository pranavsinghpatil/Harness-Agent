"""Backend contract test for the complete System 2 -> System 1 loop."""

from __future__ import annotations

from typing import Any

from backend.routes.harness import (
    InvestigationPayload,
    get_investigation_events,
    run_autonomous_investigation,
)
from harness.orchestration.investigation import (
    InvestigationSession,
    InvestigationStatus,
    default_investigation_store,
)


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
    payload: InvestigationPayload = InvestigationPayload(
        objective="Validate the complete autonomous investigation loop.",
        scenario_id="showcase_normal_baseline",
        hardware_preset_id="RDK_X5",
        seed=1337,
        budget=2,
        max_boundary_steps=0,
        max_sim_time=0.2,
    )
    snapshot: dict[str, Any] = run_autonomous_investigation(payload)
    investigation_id: str = str(snapshot["investigation_id"])

    session: InvestigationSession | None = default_investigation_store.get(investigation_id)
    assert session is not None
    assert session.wait(timeout=10.0) is True
    assert session.status == InvestigationStatus.COMPLETED

    events: list[dict[str, Any]] = get_investigation_events(investigation_id)
    assert len(events) > 0
    assert events[-1]["type"] == "INVESTIGATION_COMPLETED"
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

    experiment_id: str = next(
        str(event["experiment_id"])
        for event in events
        if event["type"] == "EXPERIMENT_STARTED"
    )
    experiment_events: list[dict[str, Any]] = [
        event for event in events if event.get("experiment_id") == experiment_id
    ]
    experiment_started: int = _first_index(experiment_events, "EXPERIMENT_STARTED")
    perception_scheduled: int = _first_index(experiment_events, "PERCEPTION_TASK_SCHEDULED")
    perception_started: int = _first_index(
        experiment_events, "COMPUTE_STARTED", name="perception"
    )
    observation_available: int = _first_index(experiment_events, "OBSERVATION_AVAILABLE")
    controller_scheduled: int = _first_index(
        experiment_events, "CONTROLLER_TASK_SCHEDULED"
    )
    controller_started: int = _first_index(
        experiment_events, "COMPUTE_STARTED", name="controller"
    )
    command_issued: int = _first_index(experiment_events, "COMMAND_ISSUED")
    actuator_applied: int = _first_index(experiment_events, "ACTUATOR_APPLIED")
    experiment_completed: int = _first_index(experiment_events, "EXPERIMENT_COMPLETED")

    assert experiment_started < perception_scheduled < perception_started
    assert perception_started < observation_available < experiment_completed
    assert controller_scheduled < command_issued
    assert controller_started < command_issued
    assert command_issued < actuator_applied < experiment_completed

    assert len({event["event_id"] for event in events}) == len(events)
    assert all(event["investigation_id"] == investigation_id for event in events)

    system1_types: set[str] = {
        "PERCEPTION_TASK_SCHEDULED",
        "OBSERVATION_AVAILABLE",
        "CONTROLLER_TASK_SCHEDULED",
        "COMMAND_ISSUED",
        "ACTUATOR_APPLIED",
    }
    for event in events:
        if event["type"] in system1_types:
            assert event.get("experiment_id")
            assert event.get("evaluation_id")
            assert event.get("run_id")
            assert event.get("episode_id")
