"""Collision detection algorithms between vehicle polygon and world entities."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from sandbox.world.geometry import Vec2D, Polygon2D, Segment2D
from sandbox.world.map import WorldMap
from sandbox.world.entities import Entity


@dataclass
class CollisionResult:
    is_collision: bool = False
    collided_entity_id: Optional[str] = None
    min_clearance: float = float("inf")
    closest_entity_id: Optional[str] = None


class CollisionDetector:
    """Evaluates collisions and minimum clearance metrics between agent and environment."""

    @staticmethod
    def evaluate(vehicle_poly: Polygon2D, world_map: WorldMap) -> CollisionResult:
        """Evaluates geometric collisions and true footprint clearance against all obstacles and walls.

        Args:
            vehicle_poly: The oriented 2D bounding polygon of the vehicle.
            world_map: The WorldMap containing boundary walls and static/dynamic obstacles.

        Returns:
            CollisionResult containing is_collision, collided_entity_id, min_clearance, and closest_entity_id.
        """
        result = CollisionResult()

        for idx, wall in enumerate(world_map.boundary_walls):
            wall_dist: float = vehicle_poly.min_distance_to_segment(wall)
            if wall_dist <= 1e-4:
                result.is_collision = True
                result.collided_entity_id = f"boundary_wall_{idx}"
                result.min_clearance = 0.0
                result.closest_entity_id = f"boundary_wall_{idx}"
                return result

            if wall_dist < result.min_clearance:
                result.min_clearance = wall_dist
                result.closest_entity_id = f"boundary_wall_{idx}"

        # 2. Evaluate clearance and collision against obstacles
        for obstacle in world_map.get_all_obstacles():
            obs_poly = obstacle.get_polygon()
            if vehicle_poly.intersects(obs_poly):
                result.is_collision = True
                result.collided_entity_id = obstacle.id
                result.min_clearance = 0.0
                result.closest_entity_id = obstacle.id
                return result

            obs_dist = vehicle_poly.min_distance_to_polygon(obs_poly)
            if obs_dist < result.min_clearance:
                result.min_clearance = obs_dist
                result.closest_entity_id = obstacle.id

        return result
