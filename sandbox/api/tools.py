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
    """Parse and register a scenario from dictionary or YAML/JSON string."""
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
    return _SCENARIO_REGISTRY.get(scenario_id)


def list_scenarios() -> list[str]:
    return list(_SCENARIO_REGISTRY.keys())


def run_episode(
    scenario: ScenarioDefinition | str,
    target_agent: BaseTargetAgent | None = None,
    seed: int | None = None,
    max_sim_time: float | None = None,
    run_id: str | None = None,
) -> tuple[RunManifest, list[TelemetryFrame]]:
    """Executes a simulation episode given a scenario or scenario_id."""
    if isinstance(scenario, str):
        sc_obj = _SCENARIO_REGISTRY.get(scenario)
        if not sc_obj:
            raise ValueError(f"Scenario '{scenario}' not found in registry")
    else:
        sc_obj = scenario

    if seed is not None:
        sc_obj.seed = seed

    agent = target_agent or ReferenceAutonomousAgent()
    env = SandboxEnvironment(scenario=sc_obj, target_agent=agent, run_id=run_id)
    manifest, frames = env.run_episode(max_sim_time=max_sim_time)

    # Cache run for query/replay
    _RUN_STORAGE[manifest.run_id] = (manifest, frames)
    return manifest, frames


def get_run(run_id: str) -> Optional[tuple[RunManifest, list[TelemetryFrame]]]:
    return _RUN_STORAGE.get(run_id)


def replay_run(
    run_id: str,
    target_agent: BaseTargetAgent | None = None,
) -> tuple[RunManifest, list[TelemetryFrame], ReplayComparisonResult]:
    """Re-executes an existing run and verifies determinism against original trace hash."""
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
    )
    comparison.original_trace_hash = orig_manifest.trace_hash
    comparison.replayed_trace_hash = replayed_manifest.trace_hash

    return replayed_manifest, replayed_frames, comparison
