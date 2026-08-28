"""Tests for 2D kinematic vehicle dynamics, SAT polygon collision, and raycasting."""

import math
from sandbox.world.geometry import Vec2D, Polygon2D, Segment2D
from sandbox.world.entities import StaticObstacle, DynamicObstacle
from sandbox.world.map import WorldMap
from sandbox.physics.dynamics import KinematicVehicleModel, VehicleState, VehicleParams
from sandbox.physics.collision import CollisionDetector


def test_vec2d_arithmetic():
    v1 = Vec2D(3.0, 4.0)
    v2 = Vec2D(1.0, 2.0)
    assert (v1 + v2) == Vec2D(4.0, 6.0)
    assert (v1 - v2) == Vec2D(2.0, 2.0)
    assert v1.magnitude == 5.0
    assert v1.dot(v2) == 11.0


def test_sat_polygon_intersection():
    poly1 = Polygon2D.from_box(center=Vec2D(0.0, 0.0), width=2.0, length=2.0, heading=0.0)
    # Overlapping box
    poly2 = Polygon2D.from_box(center=Vec2D(1.5, 0.0), width=2.0, length=2.0, heading=0.0)
    # Disjoint box
    poly3 = Polygon2D.from_box(center=Vec2D(10.0, 10.0), width=2.0, length=2.0, heading=0.0)

    assert poly1.intersects(poly2) is True
    assert poly1.intersects(poly3) is False


def test_vehicle_acceleration_and_braking():
    model = KinematicVehicleModel()
    model.set_state(VehicleState(position=Vec2D(0.0, 0.0), velocity=0.0))

    # Apply throttle = 1.0 for 1.0 second (100 steps of dt = 0.01)
    for _ in range(100):
        model.step(throttle=1.0, brake=0.0, steering_target=0.0, emergency_stop=False, dt=0.01)

    assert model.state.velocity > 2.0
    assert model.state.position.x > 1.0

    # Apply full brake = 1.0 for 1.0 second
    for _ in range(100):
        model.step(throttle=0.0, brake=1.0, steering_target=0.0, emergency_stop=False, dt=0.01)

    assert model.state.velocity == 0.0  # Stopped smoothly without flipping into negative reverse


def test_collision_detector():
    world_map = WorldMap(width=50.0, height=50.0)
    obs = StaticObstacle(id="obs_1", position=Vec2D(10.0, 10.0), width=2.0, length=2.0)
    world_map.add_static_obstacle(obs)

    # Vehicle far away from obstacle and inside map
    veh_poly_far = Polygon2D.from_box(center=Vec2D(5.0, 5.0), width=1.0, length=1.0)
    res_far = CollisionDetector.evaluate(veh_poly_far, world_map)
    assert res_far.is_collision is False
    assert res_far.min_clearance > 3.0

    # Vehicle colliding with obstacle
    veh_poly_colliding = Polygon2D.from_box(center=Vec2D(10.5, 10.0), width=1.0, length=1.0)
    res_colliding = CollisionDetector.evaluate(veh_poly_colliding, world_map)
    assert res_colliding.is_collision is True
    assert res_colliding.collided_entity_id == "obs_1"
