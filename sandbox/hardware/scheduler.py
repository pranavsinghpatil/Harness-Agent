"""Virtual edge compute scheduler modeling queue growth, deadline misses, and thermal throttling."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from sandbox.hardware.profile import HardwareProfile, ComputeTask, SchedulerPolicy


@dataclass
class HardwareMetrics:
    queue_depth: int = 0
    cpu_utilization: float = 0.0
    temperature_celsius: float = 35.0
    is_throttled: bool = False
    total_completed_tasks: int = 0
    total_dropped_tasks: int = 0
    total_deadline_misses: int = 0


class VirtualEdgeScheduler:
    """Simulates edge compute processor scheduling, queueing latency, and thermal state."""

    def __init__(self, profile: HardwareProfile | None = None) -> None:
        self.profile = profile or HardwareProfile()
        self.task_queue: list[ComputeTask] = []
        self.completed_tasks: list[ComputeTask] = []
        self.deadline_miss_events: list[dict[str, float | str]] = []
        self.metrics = HardwareMetrics()

    def submit_task(self, task: ComputeTask) -> bool:
        """Submit a task to the compute queue. Returns False if queue capacity exceeded."""
        if len(self.task_queue) >= self.profile.max_queue_depth:
            self.metrics.total_dropped_tasks += 1
            return False

        self.task_queue.append(task)
        self._sort_queue()
        return True

    def _sort_queue(self) -> None:
        """Order tasks according to active scheduling policy."""
        if self.profile.scheduler_policy == SchedulerPolicy.FIFO:
            pass  # Already insertion-ordered
        elif self.profile.scheduler_policy == SchedulerPolicy.PRIORITY:
            self.task_queue.sort(key=lambda t: t.priority)
        elif self.profile.scheduler_policy == SchedulerPolicy.EDF:
            self.task_queue.sort(key=lambda t: t.deadline)

    def _update_thermal_state(self, dt: float) -> None:
        """Updates processor temperature based on load and applies throttling if threshold exceeded."""
        busy_factor = 1.0 if self.task_queue else 0.1
        temp_delta = (
            self.profile.thermal_heat_coeff * busy_factor * 100.0 * dt
            - self.profile.thermal_cool_coeff * (self.profile.current_temperature - self.profile.thermal_ambient_temp) * dt
        )
        self.profile.current_temperature = max(
            self.profile.thermal_ambient_temp,
            self.profile.current_temperature + temp_delta,
        )

        if self.profile.current_temperature >= self.profile.thermal_throttle_temp:
            self.profile.is_throttled = True
            self.profile.effective_cpu_ratio = 0.4
        elif self.profile.current_temperature < self.profile.thermal_throttle_temp - 5.0:
            self.profile.is_throttled = False
            self.profile.effective_cpu_ratio = 1.0

    def _process_task_queue(self, sim_time: float, dt: float) -> tuple[list[ComputeTask], float]:
        """Executes queued compute tasks given available CPU capacity in time slice dt."""
        available_compute: float = (
            self.profile.cpu_capacity_units_per_sec
            * self.profile.effective_cpu_ratio
            * self.profile.cpu_availability_ratio
            * dt
        )
        just_completed: list[ComputeTask] = []

        while self.task_queue and available_compute > 0:
            current_task = self.task_queue[0]
            needed = current_task.compute_cost_units - current_task.progress_units

            if available_compute >= needed:
                available_compute -= needed
                current_task.progress_units = current_task.compute_cost_units
                current_task.is_completed = True
                self.task_queue.pop(0)

                if sim_time > current_task.deadline:
                    if not current_task.is_deadline_missed:
                        current_task.is_deadline_missed = True
                        self.metrics.total_deadline_misses += 1
                        self.deadline_miss_events.append(
                            {
                                "task_id": current_task.task_id,
                                "name": current_task.name,
                                "sim_time": sim_time,
                                "deadline": current_task.deadline,
                                "lateness": sim_time - current_task.deadline,
                            }
                        )

                just_completed.append(current_task)
                self.completed_tasks.append(current_task)
                self.metrics.total_completed_tasks += 1
            else:
                current_task.progress_units += available_compute
                available_compute = 0.0

        return just_completed, available_compute

    def _audit_remaining_deadlines(self, sim_time: float) -> None:
        """Checks if any remaining in-queue tasks have exceeded their deadline timestamp."""
        for task in self.task_queue:
            if sim_time > task.deadline and not task.is_deadline_missed:
                task.is_deadline_missed = True
                self.metrics.total_deadline_misses += 1
                self.deadline_miss_events.append(
                    {
                        "task_id": task.task_id,
                        "name": task.name,
                        "sim_time": sim_time,
                        "deadline": task.deadline,
                        "lateness": sim_time - task.deadline,
                    }
                )

    def _update_metrics(self, available_compute: float, dt: float) -> None:
        """Updates internal telemetry metrics for queue depth, utilization, and temperature."""
        self.metrics.queue_depth = len(self.task_queue)
        self.metrics.temperature_celsius = round(self.profile.current_temperature, 1)
        self.metrics.is_throttled = self.profile.is_throttled
        self.metrics.cpu_utilization = round(
            1.0 - (available_compute / max(1e-5, self.profile.cpu_capacity_units_per_sec * dt)), 2
        )

    def step(self, sim_time: float, dt: float) -> list[ComputeTask]:
        """Processes scheduled compute tasks for a timestep dt and updates hardware thermal state.

        Args:
            sim_time: Current simulation timestamp in seconds.
            dt: Timestep duration in seconds (early return with empty list if dt <= 0).

        Returns:
            list[ComputeTask]: List of tasks completed during this timestep slice.
        """
        if dt <= 0:
            return []

        self._update_thermal_state(dt)
        just_completed, remaining_compute = self._process_task_queue(sim_time, dt)
        self._audit_remaining_deadlines(sim_time)
        self._update_metrics(remaining_compute, dt)

        return just_completed

    def reset(self) -> None:
        """Resets task queues, completed history, metrics, and temperature to ambient baseline."""
        self.task_queue.clear()
        self.completed_tasks.clear()
        self.deadline_miss_events.clear()
        self.profile.current_temperature = self.profile.thermal_ambient_temp
        self.profile.is_throttled = False
        self.profile.effective_cpu_ratio = 1.0
        self.profile.cpu_availability_ratio = 1.0
        self.metrics = HardwareMetrics()
