"""Physics engine coordinating vehicle dynamics, dynamic obstacle integration, and collisions."""

from __future__ import annotations
from dataclasses import dataclass
from sandbox.world.map import WorldMap
from sandbox.physics.dynamics import KinematicVehicleModel, VehicleState, VehicleParams
from sandbox.physics.collision import CollisionDetector, CollisionResult


class PhysicsEngine:
    """Coordinates physical simulation stepping, integrations, and collision checks."""

    def __init__(self, world_map: WorldMap, vehicle_params: VehicleParams | None = None) -> None:
        self.world_map = world_map
        self.vehicle = KinematicVehicleModel(vehicle_params)
        self.latest_collision = CollisionResult()

    def reset(self, initial_state: VehicleState | None = None) -> None:
        if initial_state:
            self.vehicle.set_state(initial_state)
        else:
            self.vehicle.set_state(VehicleState())
        self.latest_collision = CollisionResult()

    def step(
        self,
        throttle: float,
        brake: float,
        steering: float,
        emergency_stop: bool,
        dt: float,
    ) -> tuple[VehicleState, CollisionResult]:
        """Advance the physics world by dt."""
        # 1. Update dynamic obstacles
        self.world_map.update_dynamic_obstacles(dt)

        # 2. Integrate vehicle model
        vehicle_state = self.vehicle.step(
            throttle=throttle,
            brake=brake,
            steering_target=steering,
            emergency_stop=emergency_stop,
            dt=dt,
        )

        # 3. Collision check
        vehicle_poly = self.vehicle.get_polygon()
        self.latest_collision = CollisionDetector.evaluate(vehicle_poly, self.world_map)

        return vehicle_state, self.latest_collision
