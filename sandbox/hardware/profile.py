"""Virtual edge compute hardware profile, task specifications, and resource constraints."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from enum import Enum


class SchedulerPolicy(str, Enum):
    FIFO = "fifo"
    PRIORITY = "priority"
    EDF = "earliest_deadline_first"


@dataclass
class ComputeTask:
    """A computational unit of work (e.g., perception inference, path search, control loop)."""
    task_id: str
    name: str
    compute_cost_units: float  # CPU units required to complete
    memory_cost_mb: float = 10.0
    deadline: float = float("inf")  # Max allowed completion sim_time
    priority: int = 10  # Lower number = higher priority
    input_timestamp: float = 0.0
    progress_units: float = 0.0
    is_completed: bool = False
    is_deadline_missed: bool = False
    result_payload: Any = None


@dataclass
class HardwareProfile:
    """Resource specifications of the virtual edge processor (e.g., Raspberry Pi, Jetson Orin Nano)."""
    cpu_capacity_units_per_sec: float = 100.0  # Max compute operations/sec
    memory_total_mb: float = 2048.0
    scheduler_policy: SchedulerPolicy = SchedulerPolicy.FIFO
    max_queue_depth: int = 20
    thermal_ambient_temp: float = 35.0  # Celsius
    thermal_throttle_temp: float = 80.0  # Celsius
    current_temperature: float = 35.0
    thermal_heat_coeff: float = 0.05
    thermal_cool_coeff: float = 0.02
    is_throttled: bool = False
    effective_cpu_ratio: float = 1.0
