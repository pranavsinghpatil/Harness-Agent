"""Scenario schema definitions for reproducible experiment configurations."""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field
from sandbox.faults.schema import FaultDefinition


class AgentInitialState(BaseModel):
    x: float = 2.0
    y: float = 25.0
    heading: float = 0.0
    velocity: float = 0.0


class ObstacleSpec(BaseModel):
    id: str
    type: str = "static"  # static or dynamic
    x: float
    y: float
    width: float = 1.5
    length: float = 1.5
    heading: float = 0.0
    target_speed: float = 0.0
    waypoints: list[list[float]] = Field(default_factory=list)


class WorldSpec(BaseModel):
    width: float = 50.0
    height: float = 50.0
    goal: list[float] = Field(default_factory=lambda: [45.0, 25.0])
    initial_state: AgentInitialState = Field(default_factory=AgentInitialState)
    obstacles: list[ObstacleSpec] = Field(default_factory=list)


class ScenarioDefinition(BaseModel):
    """Complete, self-contained specification of a simulation scenario."""
    id: str = Field(..., description="Unique scenario identifier")
    name: str = Field(default="", description="Human-readable title")
    description: str = Field(default="", description="Detailed summary of test objective")
    seed: int = Field(default=42, description="Master RNG seed")
    max_sim_time: float = Field(default=20.0, description="Max episode duration in seconds")
    world: WorldSpec = Field(default_factory=WorldSpec)
    fault_schedule: list[FaultDefinition] = Field(default_factory=list)
    safety_thresholds: dict[str, float] = Field(
        default_factory=lambda: {
            "min_clearance": 0.8,
            "speed_limit": 6.5,
            "max_observation_age_s": 0.4,
        }
    )
