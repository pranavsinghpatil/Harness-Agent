"""World entities: Base Entity, Static obstacles, and Dynamic moving obstacles."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Sequence
from sandbox.world.geometry import Vec2D, Polygon2D


@dataclass
class Entity:
    """Base class for all physical entities in the simulation world."""
    id: str
    position: Vec2D
    heading: float = 0.0  # Radians
    velocity: Vec2D = field(default_factory=lambda: Vec2D(0.0, 0.0))
    angular_velocity: float = 0.0  # Rad/s
    width: float = 1.0  # meters
    length: float = 1.5  # meters
    is_active: bool = True

    def get_polygon(self) -> Polygon2D:
        """Returns the oriented bounding polygon in world coordinates."""
        return Polygon2D.from_box(
            center=self.position,
            width=self.width,
            length=self.length,
            heading=self.heading,
        )


@dataclass
class StaticObstacle(Entity):
    """A fixed static obstacle (wall, pillar, parked vehicle, barrier)."""
    pass


@dataclass
class DynamicObstacle(Entity):
    """A moving obstacle with predefined trajectory, velocity, or reactive behavior."""
    target_speed: float = 0.0
    waypoints: list[Vec2D] = field(default_factory=list)
    current_waypoint_idx: int = 0
    loop_waypoints: bool = False

    def update(self, dt: float) -> None:
        """Advance dynamic obstacle position along its trajectory or constant velocity."""
        if not self.is_active or dt <= 0:
            return

        if self.waypoints and self.current_waypoint_idx < len(self.waypoints):
            target_wp = self.waypoints[self.current_waypoint_idx]
            to_target = target_wp - self.position
            dist = to_target.magnitude

            if dist < 0.2:
                # Reached waypoint
                self.current_waypoint_idx += 1
                if self.current_waypoint_idx >= len(self.waypoints):
                    if self.loop_waypoints:
                        self.current_waypoint_idx = 0
                    else:
                        self.velocity = Vec2D(0.0, 0.0)
                        return

            if dist > 0.01:
                direction = to_target.normalized()
                self.velocity = direction * self.target_speed
                self.heading = direction.to_tuple()[1]  # or angle
                import math
                self.heading = math.atan2(direction.y, direction.x)
                self.position = self.position + self.velocity * dt
        else:
            # Simple ballistic trajectory from velocity
            self.position = self.position + self.velocity * dt
