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
        result = CollisionResult()
        center = Vec2D(
            sum(v.x for v in vehicle_poly.vertices) / len(vehicle_poly.vertices),
            sum(v.y for v in vehicle_poly.vertices) / len(vehicle_poly.vertices),
        )

        # 1. Check against boundary walls
        for idx, wall in enumerate(world_map.boundary_walls):
            # Check edge-edge intersection
            for v_edge in vehicle_poly.get_edges():
                # Segment intersection check
                t = wall.intersect_ray(v_edge.p1, (v_edge.p2 - v_edge.p1).normalized(), v_edge.length())
                if t is not None:
                    result.is_collision = True
                    result.collided_entity_id = f"boundary_wall_{idx}"
                    result.min_clearance = 0.0
                    return result

        # 2. Check against all obstacles
        for obstacle in world_map.get_all_obstacles():
            obs_poly = obstacle.get_polygon()
            if vehicle_poly.intersects(obs_poly):
                result.is_collision = True
                result.collided_entity_id = obstacle.id
                result.min_clearance = 0.0
                return result

            # Compute clearance
            dist = obs_poly.min_distance_to_point(center)
            if dist < result.min_clearance:
                result.min_clearance = dist
                result.closest_entity_id = obstacle.id

        return result
