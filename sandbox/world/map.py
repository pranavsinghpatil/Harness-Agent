"""World map definition, boundaries, and spatial obstacle query engine."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from sandbox.world.geometry import Vec2D, Polygon2D, Segment2D
from sandbox.world.entities import Entity, StaticObstacle, DynamicObstacle


@dataclass
class WorldMap:
    """Manages the 2D arena layout, boundaries, obstacles, and navigation goals."""
    width: float = 50.0  # meters
    height: float = 50.0  # meters
    goal_position: Vec2D = field(default_factory=lambda: Vec2D(40.0, 25.0))
    static_obstacles: list[StaticObstacle] = field(default_factory=list)
    dynamic_obstacles: list[DynamicObstacle] = field(default_factory=list)
    boundary_walls: list[Segment2D] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.boundary_walls:
            self._create_default_boundaries()

    def _create_default_boundaries(self) -> None:
        """Create outer bounding walls for the map."""
        p1 = Vec2D(0.0, 0.0)
        p2 = Vec2D(self.width, 0.0)
        p3 = Vec2D(self.width, self.height)
        p4 = Vec2D(0.0, self.height)
        self.boundary_walls = [
            Segment2D(p1, p2),
            Segment2D(p2, p3),
            Segment2D(p3, p4),
            Segment2D(p4, p1),
        ]

    def add_static_obstacle(self, obstacle: StaticObstacle) -> None:
        self.static_obstacles.append(obstacle)

    def add_dynamic_obstacle(self, obstacle: DynamicObstacle) -> None:
        self.dynamic_obstacles.append(obstacle)

    def update_dynamic_obstacles(self, dt: float) -> None:
        """Step all active dynamic obstacles forward in time."""
        for dyn in self.dynamic_obstacles:
            dyn.update(dt)

    def raycast(self, origin: Vec2D, direction: Vec2D, max_range: float) -> tuple[Optional[float], Optional[str]]:
        """Raycasts against boundary walls and all obstacles, returning (min_distance, hit_entity_id)."""
        min_dist: Optional[float] = None
        hit_id: Optional[str] = None

        # 1. Check boundary walls
        for wall in self.boundary_walls:
            d = wall.intersect_ray(origin, direction, max_range)
            if d is not None and (min_dist is None or d < min_dist):
                min_dist = d
                hit_id = "boundary_wall"

        # 2. Check static obstacles
        for obs in self.static_obstacles:
            if not obs.is_active:
                continue
            poly = obs.get_polygon()
            d = poly.raycast(origin, direction, max_range)
            if d is not None and (min_dist is None or d < min_dist):
                min_dist = d
                hit_id = obs.id

        # 3. Check dynamic obstacles
        for dyn in self.dynamic_obstacles:
            if not dyn.is_active:
                continue
            poly = dyn.get_polygon()
            d = poly.raycast(origin, direction, max_range)
            if d is not None and (min_dist is None or d < min_dist):
                min_dist = d
                hit_id = dyn.id

        return min_dist, hit_id

    def get_all_obstacles(self) -> list[Entity]:
        """Return combined active obstacles."""
        return [o for o in self.static_obstacles if o.is_active] + [
            d for d in self.dynamic_obstacles if d.is_active
        ]
