"""RunManifest schema for reproducible simulation episode runs and replays."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class RunManifest(BaseModel):
    """Immutable manifest capturing the exact configuration and outcome of an episode."""
    run_id: str = Field(..., description="Unique episode run identifier")
    seed: int = Field(..., description="Master RNG seed")
    scenario_id: str = Field(..., description="Scenario identifier")
    scenario_hash: str = Field(default="", description="SHA256 hash of scenario definition")
    hardware_profile_hash: str = Field(default="", description="SHA256 hash of hardware configuration")
    target_agent_version: str = Field(default="reference_v1", description="Target agent model version")
    fault_ids: list[str] = Field(default_factory=list, description="IDs of faults scheduled in this run")
    status: str = Field(..., description="Final episode status e.g. completed_safe, safety_violation")
    termination_reason: str = Field(default="", description="Human-readable reason for termination")
    sim_duration_seconds: float = Field(..., description="Total simulated seconds executed")
    total_steps: int = Field(..., description="Total simulation discrete ticks")
    violations_count: int = Field(default=0, description="Total safety violations detected")
    trace_hash: str = Field(default="", description="SHA256 hash of all recorded telemetry states")
    metadata: dict[str, Any] = Field(default_factory=dict)
