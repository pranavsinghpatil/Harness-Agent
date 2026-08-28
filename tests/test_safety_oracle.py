"""Tests for ground-truth safety oracle property evaluations."""

from sandbox.world.geometry import Vec2D
from sandbox.physics.dynamics import VehicleState, VehicleParams
from sandbox.physics.collision import CollisionResult
from sandbox.actuators.command import ActuatorCommand
from sandbox.safety.oracle import SafetyOracle
from sandbox.safety.properties import Severity


def test_collision_violation() -> None:
    oracle = SafetyOracle()
    params = VehicleParams()
    state = VehicleState(position=Vec2D(10.0, 20.0), velocity=3.0)
    cmd = ActuatorCommand()

    col = CollisionResult(is_collision=True, collided_entity_id="dynamic_pedestrian")
    violations = oracle.evaluate(sim_time=2.5, state=state, params=params, collision_result=col, current_command=cmd)

    assert len(violations) >= 1
    assert any(v.rule_name == "CollisionViolation" and v.severity == Severity.FATAL for v in violations)


def test_stopping_distance_violation() -> None:
    oracle = SafetyOracle(reaction_time_s=0.2)
    params = VehicleParams(max_brake_deceleration=5.0)
    # Moving at 4.0 m/s -> d_stop = 4*0.2 + 16/(2*5) = 0.8 + 1.6 = 2.4m
    state = VehicleState(velocity=4.0)
    # Obstacle is 1.5m away, but agent is pressing throttle = 0.8
    col = CollisionResult(is_collision=False, min_clearance=1.5, closest_entity_id="barrier")
    cmd = ActuatorCommand(throttle=0.8, brake=0.0)

    violations = oracle.evaluate(sim_time=3.0, state=state, params=params, collision_result=col, current_command=cmd)
    assert any(v.rule_name == "UnsafeStoppingDistanceViolation" for v in violations)


def test_stale_observation_violation() -> None:
    oracle = SafetyOracle(max_observation_age_s=0.4)
    params = VehicleParams()
    state = VehicleState(velocity=2.5)
    col = CollisionResult(is_collision=False, min_clearance=10.0)
    cmd = ActuatorCommand(throttle=0.6, brake=0.0)

    # Observation age = 0.8s > 0.4s while moving
    violations = oracle.evaluate(
        sim_time=4.0,
        state=state,
        params=params,
        collision_result=col,
        current_command=cmd,
        observation_age_s=0.8,
    )
    assert any(v.rule_name == "StaleObservationActionViolation" for v in violations)
