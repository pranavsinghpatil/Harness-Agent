"""Stable programmatic API tools for creating, executing, inspecting, and replaying simulations."""

from __future__ import annotations
import json
import yaml
from pathlib import Path
from typing import Any, Optional
from scenarios.schema import ScenarioDefinition
from sandbox.api.environment import SandboxEnvironment
from sandbox.telemetry.manifest import RunManifest
from sandbox.telemetry.recorder import TelemetryFrame
from sandbox.telemetry.replay import DeterministicReplayer, ReplayComparisonResult
from target_agents.base import BaseTargetAgent
from target_agents.reference_agent.agent import ReferenceAutonomousAgent


# In-memory registry for scenarios and run artifacts
_SCENARIO_REGISTRY: dict[str, ScenarioDefinition] = {}
_RUN_STORAGE: dict[str, tuple[RunManifest, list[TelemetryFrame]]] = {}


def create_scenario(spec: dict[str, Any] | str) -> ScenarioDefinition:
    """Parse, validate, and register a ScenarioDefinition from a dictionary or YAML/JSON string.

    Args:
        spec: Raw scenario dictionary or YAML/JSON specification string.

    Returns:
        ScenarioDefinition: The validated and registered scenario model.

    Raises:
        ValueError: If parsing fails or the specification does not conform to ScenarioDefinition schema.
    """
    if isinstance(spec, str):
        try:
            data = yaml.safe_load(spec)
        except Exception:
            data = json.loads(spec)
    else:
        data = spec

    scenario = ScenarioDefinition(**data)
    _SCENARIO_REGISTRY[scenario.id] = scenario
    return scenario


def get_scenario(scenario_id: str) -> Optional[ScenarioDefinition]:
    """Retrieves a registered scenario by ID from in-memory storage.

    Args:
        scenario_id: Unique string identifier of the scenario.

    Returns:
        Optional[ScenarioDefinition]: The scenario definition if found, else None.
    """
    return _SCENARIO_REGISTRY.get(scenario_id)


def list_scenarios() -> list[str]:
    """Returns a list of all registered scenario identifiers.

    Returns:
        list[str]: Registered scenario IDs.
    """
    return list(_SCENARIO_REGISTRY.keys())


def run_episode(
    scenario: ScenarioDefinition | str,
    target_agent: BaseTargetAgent | None = None,
    seed: int | None = None,
    max_sim_time: float | None = None,
    run_id: str | None = None,
) -> tuple[RunManifest, list[TelemetryFrame]]:
    """Executes a simulation episode given a scenario or scenario_id.

    Args:
        scenario: A ScenarioDefinition instance or string ID registered in the scenario registry.
        target_agent: Optional autonomous controller under test (defaults to ReferenceAutonomousAgent).
        seed: Optional pseudo-random seed override (clones scenario without mutating registry).
        max_sim_time: Maximum simulation duration in seconds (defaults to scenario.max_duration_seconds).
        run_id: Optional custom identifier for the execution run.

    Returns:
        tuple[RunManifest, list[TelemetryFrame]]: A tuple of the final execution manifest and recorded frames.

    Raises:
        ValueError: If a scenario string ID is provided but not found in the registry.
    """
    if isinstance(scenario, str):
        sc_obj = _SCENARIO_REGISTRY.get(scenario)
        if not sc_obj:
            raise ValueError(f"Scenario '{scenario}' not found in registry")
    else:
        sc_obj = scenario

    # Clone scenario model to prevent mutating shared registry instance
    sc_copy = sc_obj.model_copy(deep=True)
    if seed is not None:
        sc_copy.seed = seed

    agent = target_agent or ReferenceAutonomousAgent()
    env = SandboxEnvironment(scenario=sc_copy, target_agent=agent, run_id=run_id)
    manifest, frames = env.run_episode(max_sim_time=max_sim_time)

    # Cache run for query/replay
    _RUN_STORAGE[manifest.run_id] = (manifest, frames)
    return manifest, frames


def get_run(run_id: str) -> Optional[tuple[RunManifest, list[TelemetryFrame]]]:
    """Retrieves cached execution run manifest and recorded telemetry frames.

    Args:
        run_id: Unique string identifier of the execution run.

    Returns:
        Optional[tuple[RunManifest, list[TelemetryFrame]]]: Cached manifest and frames tuple, or None.
    """
    return _RUN_STORAGE.get(run_id)


def replay_run(
    run_id: str,
    target_agent: BaseTargetAgent | None = None,
) -> tuple[RunManifest, list[TelemetryFrame], ReplayComparisonResult]:
    """Re-executes an existing run and verifies bit-exact determinism against original trace hash.

    Args:
        run_id: Unique string identifier of the original run to replay.
        target_agent: Optional autonomous controller under test (defaults to ReferenceAutonomousAgent).

    Returns:
        tuple[RunManifest, list[TelemetryFrame], ReplayComparisonResult]: Replayed manifest, frames, and comparison verdict.

    Raises:
        ValueError: If run_id is not found in run storage or the scenario is missing.
    """
    cached = _RUN_STORAGE.get(run_id)
    if not cached:
        raise ValueError(f"Run ID '{run_id}' not found in run storage")

    orig_manifest, orig_frames = cached
    scenario = _SCENARIO_REGISTRY.get(orig_manifest.scenario_id)
    if not scenario:
        raise ValueError(f"Scenario '{orig_manifest.scenario_id}' no longer in registry")

    agent = target_agent or ReferenceAutonomousAgent()
    replayed_manifest, replayed_frames = run_episode(
        scenario=scenario,
        target_agent=agent,
        seed=orig_manifest.seed,
        max_sim_time=orig_manifest.sim_duration_seconds,
        run_id=f"replay_{run_id}",
    )

    comparison = DeterministicReplayer.compare_traces(
        [f.to_dict() for f in orig_frames],
        [f.to_dict() for f in replayed_frames],
        orig_hash=orig_manifest.trace_hash,
        rep_hash=replayed_manifest.trace_hash,
    )

    return replayed_manifest, replayed_frames, comparison
