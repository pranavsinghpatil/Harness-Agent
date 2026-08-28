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

    def evaluate(
        self,
        sim_time: float,
        state: VehicleState,
        params: VehicleParams,
        collision_result: CollisionResult,
        current_command: ActuatorCommand,
        observation_age_s: float = 0.0,
    ) -> list[SafetyViolation]:
        """Runs all safety property checks against current ground truth."""
        new_violations: list[SafetyViolation] = []

        # 1. Collision Rule
        if collision_result.is_collision:
            v = SafetyViolation(
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
            new_violations.append(v)

        # 2. Minimum Clearance Margin Rule
        elif collision_result.min_clearance < self.min_clearance_threshold:
            v = SafetyViolation(
                rule_name="MinClearanceViolation",
                timestamp=sim_time,
                severity=Severity.WARNING,
                description=f"Clearance {collision_result.min_clearance:.2f}m is below safe threshold {self.min_clearance_threshold}m",
                details={
                    "min_clearance": round(collision_result.min_clearance, 3),
                    "closest_entity_id": collision_result.closest_entity_id,
                },
            )
            new_violations.append(v)

        # 3. Unsafe Stopping Distance Rule
        # d_stop = v * t_reaction + v^2 / (2 * a_brake)
        if state.velocity > 0.5:
            d_stop = (
                state.velocity * self.reaction_time_s
                + (state.velocity ** 2) / (2.0 * max(0.5, params.max_brake_deceleration))
            )
            if collision_result.min_clearance < d_stop and current_command.throttle > 0.2:
                v = SafetyViolation(
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
                new_violations.append(v)

        # 4. Speed Limit Invariant
        if state.velocity > self.speed_limit:
            v = SafetyViolation(
                rule_name="SpeedLimitViolation",
                timestamp=sim_time,
                severity=Severity.WARNING,
                description=f"Vehicle velocity {state.velocity:.2f}m/s exceeds speed limit {self.speed_limit}m/s",
                details={"velocity": round(state.velocity, 3), "limit": self.speed_limit},
            )
            new_violations.append(v)

        # 5. Stale Observation Action Rule
        if observation_age_s > self.max_observation_age_s and state.velocity > 1.5 and current_command.throttle > 0.1:
            v = SafetyViolation(
                rule_name="StaleObservationActionViolation",
                timestamp=sim_time,
                severity=Severity.CRITICAL,
                description=f"Agent accelerating with stale sensor observations ({observation_age_s:.3f}s old)",
                details={"observation_age_s": round(observation_age_s, 3), "velocity": round(state.velocity, 3)},
            )
            new_violations.append(v)

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
