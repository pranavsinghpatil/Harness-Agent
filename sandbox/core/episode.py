"""Episode lifecycle management, termination checks, and status tracking."""

from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class EpisodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED_SAFE = "completed_safe"
    SAFETY_VIOLATION = "safety_violation"
    TIMEOUT = "timeout"
    GOAL_REACHED = "goal_reached"
    ABORTED = "aborted"


class EpisodeConfig(BaseModel):
    """Configuration governing an episode execution."""
    max_sim_time: float = Field(default=30.0, description="Max simulation time in seconds")
    fixed_dt: float = Field(default=0.01, description="Base physics tick rate (100 Hz = 0.01s)")
    seed: int = Field(default=42, description="RNG master seed")
    terminate_on_collision: bool = Field(default=True, description="Stop immediately on collision")
    terminate_on_safety_violation: bool = Field(
        default=False, description="Stop immediately on any safety rule breach"
    )
    goal_tolerance: float = Field(default=0.5, description="Distance threshold in meters to consider goal reached")


class EpisodeLifecycle:
    """Tracks episode state transitions and termination conditions."""

    def __init__(self, config: EpisodeConfig) -> None:
        self.config = config
        self.status = EpisodeStatus.PENDING
        self.termination_reason: str = ""
        self.sim_start_time: float = 0.0
        self.sim_end_time: float = 0.0
        self.total_steps: int = 0

    @property
    def is_finished(self) -> bool:
        return self.status not in (EpisodeStatus.PENDING, EpisodeStatus.RUNNING)

    def start(self, current_time: float = 0.0) -> None:
        self.status = EpisodeStatus.RUNNING
        self.sim_start_time = current_time

    def finish(self, status: EpisodeStatus, reason: str, current_time: float) -> None:
        self.status = status
        self.termination_reason = reason
        self.sim_end_time = current_time

    def check_timeout(self, current_time: float) -> bool:
        if current_time >= self.config.max_sim_time:
            self.finish(
                EpisodeStatus.TIMEOUT,
                f"Exceeded max simulation time of {self.config.max_sim_time}s",
                current_time,
            )
            return True
        return False
