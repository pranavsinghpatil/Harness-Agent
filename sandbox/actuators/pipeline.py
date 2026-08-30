"""Actuator execution pipeline modeling command delays, response dynamics, and mechanical faults."""

from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from typing import Optional
import numpy as np
from sandbox.actuators.command import ActuatorCommand


@dataclass(order=True)
class QueuedCommand:
    apply_time: float
    command_id: int
    cmd: ActuatorCommand = field(compare=False)


class ActuatorPipeline:
    """Simulates actuator latency, response lag, and mechanical fault perturbations."""

    def __init__(
        self,
        rng: np.random.Generator | None = None,
        base_delay_s: float = 0.05,  # 50 ms mechanical delay
        jitter_std_s: float = 0.005,  # 5 ms jitter
        estop_delay_s: float = 0.01,  # 10 ms dedicated fast-path e-stop
    ) -> None:
        self.rng = rng if rng is not None else np.random.default_rng(48)
        self.base_delay_s = base_delay_s
        self.jitter_std_s = jitter_std_s
        self.estop_delay_s = estop_delay_s

        self._queue: list[QueuedCommand] = []
        self._current_applied_cmd = ActuatorCommand()
        self.applied_commands_this_step: list[ActuatorCommand] = []
        self.cmd_counter: int = 0

        # Fault state injection hooks
        self.stuck_steering_angle: Optional[float] = None
        self.brake_effectiveness_factor: float = 1.0  # 1.0 = normal, 0.0 = total brake loss
        self.throttle_effectiveness_factor: float = 1.0
        self.dropped_command_prob: float = 0.0
        self.extra_delay_s: float = 0.0

    def submit_command(self, cmd: ActuatorCommand, current_sim_time: float) -> bool:
        """Submit a command to the actuator queue."""
        self.cmd_counter += 1
        cmd.command_id = self.cmd_counter
        cmd.sim_sent_time = current_sim_time

        # Check dropped command fault
        if self.dropped_command_prob > 0 and self.rng.uniform(0.0, 1.0) < self.dropped_command_prob:
            return False

        # E-stop takes dedicated fast path
        if cmd.emergency_stop:
            delay = self.estop_delay_s
        else:
            jitter = float(self.rng.normal(0.0, self.jitter_std_s)) if self.jitter_std_s > 0 else 0.0
            delay = max(0.001, self.base_delay_s + self.extra_delay_s + jitter)

        apply_time = round(current_sim_time + delay, 9)
        queued = QueuedCommand(apply_time=apply_time, command_id=self.cmd_counter, cmd=cmd)
        heapq.heappush(self._queue, queued)
        return True

    def step(self, current_sim_time: float) -> ActuatorCommand:
        """Applies due commands and transforms them with active fault perturbations."""
        self.applied_commands_this_step = []
        while self._queue and self._queue[0].apply_time <= current_sim_time:
            self._current_applied_cmd = heapq.heappop(self._queue).cmd
            self.applied_commands_this_step.append(self._current_applied_cmd)

        # Produce effective command factoring in mechanical perturbations
        effective_cmd = ActuatorCommand(
            throttle=self._current_applied_cmd.throttle * self.throttle_effectiveness_factor,
            brake=self._current_applied_cmd.brake * self.brake_effectiveness_factor,
            steering=(
                self.stuck_steering_angle
                if self.stuck_steering_angle is not None
                else self._current_applied_cmd.steering
            ),
            emergency_stop=self._current_applied_cmd.emergency_stop,
            command_id=self._current_applied_cmd.command_id,
            sim_sent_time=self._current_applied_cmd.sim_sent_time,
        )

        return effective_cmd

    def reset(self) -> None:
        self._queue.clear()
        self._current_applied_cmd = ActuatorCommand()
        self.applied_commands_this_step.clear()
        self.cmd_counter = 0
        self.stuck_steering_angle = None
        self.brake_effectiveness_factor = 1.0
        self.throttle_effectiveness_factor = 1.0
        self.dropped_command_prob = 0.0
        self.extra_delay_s = 0.0
