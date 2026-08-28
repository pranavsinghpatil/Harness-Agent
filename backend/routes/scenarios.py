"""FastAPI routes for scenario creation, execution, and replay."""

from __future__ import annotations
import glob
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import yaml
from scenarios.schema import ScenarioDefinition
from sandbox.api.tools import (
    create_scenario,
    get_scenario,
    list_scenarios,
    run_episode,
    replay_run,
    get_run,
)


router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


class RunRequest(BaseModel):
    scenario_id: Optional[str] = None
    scenario_spec: Optional[dict[str, Any]] = None
    seed: Optional[int] = None
    max_sim_time: Optional[float] = None


def load_bundled_scenarios() -> None:
    """Load default scenario files from the scenarios directory into memory."""
    patterns = [
        "scenarios/templates/*.yaml",
        "scenarios/generated/*.yaml",
    ]
    for pattern in patterns:
        for filepath in glob.glob(pattern):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "id" in data:
                        create_scenario(data)
            except Exception:
                pass


# Initialize bundled scenarios
load_bundled_scenarios()


@router.get("/")
def get_all_scenarios() -> list[dict[str, Any]]:
    """Lists all registered simulation scenarios."""
    load_bundled_scenarios()
    scenarios = []
    for sc_id in list_scenarios():
        sc = get_scenario(sc_id)
        if sc:
            scenarios.append(sc.model_dump())
    return scenarios


@router.get("/{scenario_id}")
def get_scenario_by_id(scenario_id: str) -> dict[str, Any]:
    sc = get_scenario(scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    return sc.model_dump()


@router.post("/run")
def execute_scenario_endpoint(req: RunRequest) -> dict[str, Any]:
    """Runs a scenario and returns the manifest and telemetry trace."""
    if req.scenario_spec:
        scenario = create_scenario(req.scenario_spec)
    elif req.scenario_id:
        scenario = get_scenario(req.scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail=f"Scenario '{req.scenario_id}' not found")
    else:
        raise HTTPException(status_code=400, detail="Must provide either scenario_id or scenario_spec")

    manifest, frames = run_episode(
        scenario=scenario,
        seed=req.seed,
        max_sim_time=req.max_sim_time,
    )

    return {
        "manifest": manifest.model_dump(),
        "total_frames": len(frames),
        "frames": [f.to_dict() for f in frames],
    }


@router.post("/replay/{run_id}")
def replay_endpoint(run_id: str) -> dict[str, Any]:
    """Replays a previous run and evaluates bit-exact trace determinism."""
    try:
        manifest, frames, comparison = replay_run(run_id)
        return {
            "replayed_manifest": manifest.model_dump(),
            "is_bit_exact_match": comparison.is_bit_exact_match,
            "original_trace_hash": comparison.original_trace_hash,
            "replayed_trace_hash": comparison.replayed_trace_hash,
            "difference_details": comparison.difference_details,
            "frames": [f.to_dict() for f in frames],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
