"""Ground-truth Safety Oracle independently verifying physical invariants and system deadlines."""

from __future__ import annotations
from typing import Any, Optional
from sandbox.safety.properties import SafetyViolation, Severity
from sandbox.physics.dynamics import VehicleState, VehicleParams
from sandbox.physics.collision import CollisionResult
from sandbox.actuators.command import ActuatorCommand


class SafetyOracle:
    """Evaluates simulation state directly against ground-truth safety invariants."""

    def __init__(
        self,
        min_clearance_threshold: float = 0.8,  # meters
        speed_limit: float = 7.0,  # m/s
        max_observation_age_s: float = 0.5,  # 500 ms max allowable sensor staleness
        reaction_time_s: float = 0.2,  # 200 ms estimated reaction buffer
    ) -> None:
        self.min_clearance_threshold = min_clearance_threshold
        self.speed_limit = speed_limit
        self.max_observation_age_s = max_observation_age_s
        self.reaction_time_s = reaction_time_s
        self.violations: list[SafetyViolation] = []

    def _check_collision(self, sim_time: float, state: VehicleState, collision_result: CollisionResult) -> Optional[SafetyViolation]:
        """Checks for fatal physical intersection with boundaries or obstacles."""
        if not collision_result.is_collision:
            return None
        return SafetyViolation(
            rule_name="CollisionViolation",
            timestamp=sim_time,
            severity=Severity.FATAL,
            description=f"Physical collision with entity: {collision_result.collided_entity_id}",
            details={
                "collided_entity_id": collision_result.collided_entity_id,
                "velocity": round(state.velocity, 3),
                "position": {"x": round(state.position.x, 3), "y": round(state.position.y, 3)},
            },
        )

    def _check_clearance(self, sim_time: float, collision_result: CollisionResult) -> Optional[SafetyViolation]:
        """Checks if vehicle clearance has breached the minimum safety threshold."""
        if collision_result.is_collision or collision_result.min_clearance >= self.min_clearance_threshold:
            return None
        return SafetyViolation(
            rule_name="MinClearanceViolation",
            timestamp=sim_time,
            severity=Severity.WARNING,
            description=f"Clearance {collision_result.min_clearance:.2f}m is below safe threshold {self.min_clearance_threshold}m",
            details={
                "min_clearance": round(collision_result.min_clearance, 3),
                "closest_entity_id": collision_result.closest_entity_id,
            },
        )

    def _check_stopping_distance(
        self,
        sim_time: float,
        state: VehicleState,
        params: VehicleParams,
        collision_result: CollisionResult,
        current_command: ActuatorCommand,
    ) -> Optional[SafetyViolation]:
        """Checks if vehicle is driving forward when obstacle is closer than the required stopping distance."""
        if state.velocity <= 0.5 or current_command.throttle <= 0.2:
            return None
        d_stop = (
            state.velocity * self.reaction_time_s
            + (state.velocity ** 2) / (2.0 * max(0.5, params.max_brake_deceleration))
        )
        if collision_result.min_clearance >= d_stop:
            return None
        return SafetyViolation(
            rule_name="UnsafeStoppingDistanceViolation",
            timestamp=sim_time,
            severity=Severity.CRITICAL,
            description=f"Obstacle distance ({collision_result.min_clearance:.2f}m) < required stopping distance ({d_stop:.2f}m) while accelerating",
            details={
                "speed": round(state.velocity, 3),
                "stopping_distance": round(d_stop, 3),
                "obstacle_clearance": round(collision_result.min_clearance, 3),
                "throttle": round(current_command.throttle, 2),
            },
        )

    def _check_speed_and_staleness(
        self,
        sim_time: float,
        state: VehicleState,
        current_command: ActuatorCommand,
        observation_age_s: float,
    ) -> list[SafetyViolation]:
        """Checks speed limit invariants and stale observation acceleration rules."""
        violations: list[SafetyViolation] = []
        if state.velocity > self.speed_limit:
            violations.append(
                SafetyViolation(
                    rule_name="SpeedLimitViolation",
                    timestamp=sim_time,
                    severity=Severity.WARNING,
                    description=f"Vehicle velocity {state.velocity:.2f}m/s exceeds speed limit {self.speed_limit}m/s",
                    details={"velocity": round(state.velocity, 3), "limit": self.speed_limit},
                )
            )

        if observation_age_s > self.max_observation_age_s and state.velocity > 1.5 and current_command.throttle > 0.1:
            violations.append(
                SafetyViolation(
                    rule_name="StaleObservationActionViolation",
                    timestamp=sim_time,
                    severity=Severity.CRITICAL,
                    description=f"Agent accelerating with stale sensor observations ({observation_age_s:.3f}s old)",
                    details={"observation_age_s": round(observation_age_s, 3), "velocity": round(state.velocity, 3)},
                )
            )

        return violations

    def evaluate(
        self,
        sim_time: float,
        state: VehicleState,
        params: VehicleParams,
        collision_result: CollisionResult,
        current_command: ActuatorCommand,
        observation_age_s: float = 0.0,
    ) -> list[SafetyViolation]:
        """Evaluates ground-truth physical state and commands against safety invariants.

        Args:
            sim_time: Current simulation timestamp in seconds.
            state: Ground-truth physical vehicle state (position, velocity, acceleration).
            params: Vehicle parameters defining maximum braking and dynamics limits.
            collision_result: Geometric collision and clearance results from CollisionDetector.
            current_command: ActuatorCommand currently applied to physical motors.
            observation_age_s: Age in seconds of the oldest active sensor stream consumed by the agent.

        Returns:
            list[SafetyViolation]: Newly detected safety violations during this step.

        Side Effects:
            Appends all newly detected violations to `self.violations`.
        """
        new_violations: list[SafetyViolation] = []

        col_v = self._check_collision(sim_time, state, collision_result)
        if col_v:
            new_violations.append(col_v)

        clr_v = self._check_clearance(sim_time, collision_result)
        if clr_v:
            new_violations.append(clr_v)

        stop_v = self._check_stopping_distance(sim_time, state, params, collision_result, current_command)
        if stop_v:
            new_violations.append(stop_v)

        new_violations.extend(self._check_speed_and_staleness(sim_time, state, current_command, observation_age_s))

        self.violations.extend(new_violations)
        return new_violations

    def reset(self) -> None:
        self.violations.clear()

    @property
    def has_fatal_violations(self) -> bool:
        return any(v.severity == Severity.FATAL for v in self.violations)

    @property
    def total_violations(self) -> int:
        return len(self.violations)
