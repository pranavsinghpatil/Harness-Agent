"""WebSocket endpoint for real-time simulation streaming to visualizer clients."""

from __future__ import annotations
import asyncio
import json
from queue import Empty
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from harness.orchestration.investigation import default_investigation_store
from sandbox.api.environment import SandboxEnvironment
from sandbox.api.tools import get_scenario, create_scenario
from target_agents.reference_agent.agent import ReferenceAutonomousAgent


router = APIRouter(tags=["websocket"])


async def _next_investigation_event(subscription: object) -> object:
    """Wait for one queued event without blocking the ASGI event loop."""
    event_queue = getattr(subscription, "queue")
    try:
        return await asyncio.to_thread(event_queue.get, True, 30.0)
    except Empty:
        return None


@router.websocket("/ws/investigations/{investigation_id}")
async def websocket_investigation_stream(websocket: WebSocket, investigation_id: str) -> None:
    """Stream an investigation's ordered lifecycle events until it reaches a terminal state.

    Args:
        websocket: Accepted client connection receiving JSON `HarnessEvent` objects.
        investigation_id: Stable session ID returned by the REST creation endpoint.

    Streams:
        Existing event history is replayed first, followed by live events. The
        socket closes normally after `INVESTIGATION_COMPLETED` or
        `INVESTIGATION_FAILED`; disconnects are treated as client cancellation.

    Errors:
        Unknown investigations receive an error payload and close code `4404`.
    """
    session = default_investigation_store.get(investigation_id)
    if session is None:
        await websocket.accept()
        await websocket.send_json({"error": f"Investigation '{investigation_id}' not found"})
        await websocket.close(code=4404)
        return

    await websocket.accept()
    subscription = session.subscribe()
    terminal_types = {"INVESTIGATION_COMPLETED", "INVESTIGATION_FAILED"}
    try:
        for event in subscription.events:
            await websocket.send_json(event.to_dict())
        if any(event.type.value in terminal_types for event in subscription.events):
            return

        while True:
            event = await _next_investigation_event(subscription)
            if event is None:
                continue
            await websocket.send_json(event.to_dict())
            if event.type.value in terminal_types:
                return
    except WebSocketDisconnect:
        pass
    finally:
        session.unsubscribe(subscription.queue)


@router.websocket("/ws/live/{scenario_id}")
async def websocket_live_stream(websocket: WebSocket, scenario_id: str) -> None:
    """Streams real-time simulation telemetry frames over WebSocket to connected frontend clients.

    Args:
        websocket: Connected FastAPI WebSocket client connection.
        scenario_id: Identifier of the registered ScenarioDefinition to simulate and stream.

    Streams:
        JSON objects containing live TelemetryFrame dictionaries and terminal RunManifest payloads.
    """
    await websocket.accept()

    scenario = get_scenario(scenario_id)
    if not scenario:
        await websocket.send_json({"error": f"Scenario '{scenario_id}' not found"})
        await websocket.close()
        return

    env = SandboxEnvironment(scenario=scenario, target_agent=ReferenceAutonomousAgent())
    env.reset()
    dt = env.episode_config.fixed_dt

    try:
        while not env.lifecycle.is_finished:
            frame = env.step(dt)
            payload = {
                "type": "frame",
                "data": frame.to_dict(),
                "status": env.lifecycle.status.value,
                "is_finished": env.lifecycle.is_finished,
            }
            await websocket.send_json(payload)
            # Control streaming speed (approx 30 fps stream)
            await asyncio.sleep(0.01)

        # Send final manifest
        manifest = {
            "type": "manifest",
            "run_id": env.run_id,
            "status": env.lifecycle.status.value,
            "termination_reason": env.lifecycle.termination_reason,
            "duration": env.clock.current_time,
            "steps": env.clock.step_count,
            "violations_count": env.safety.total_violations,
            "trace_hash": env.telemetry.compute_trace_hash(),
        }
        await websocket.send_json(manifest)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
