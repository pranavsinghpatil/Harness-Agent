"""2D Geometry primitives, vector arithmetic, raycasting, and SAT collision algorithms."""

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Optional, Sequence


@dataclass(frozen=True)
class Vec2D:
    x: float
    y: float

    def __add__(self, other: Vec2D) -> Vec2D:
        return Vec2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vec2D) -> Vec2D:
        return Vec2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vec2D:
        return Vec2D(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vec2D:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vec2D:
        if scalar == 0:
            raise ZeroDivisionError("Cannot divide Vec2D by zero")
        return Vec2D(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vec2D:
        return Vec2D(-self.x, -self.y)

    def dot(self, other: Vec2D) -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vec2D) -> float:
        return self.x * other.y - self.y * other.x

    @property
    def magnitude_sq(self) -> float:
        return self.x * self.x + self.y * self.y

    @property
    def magnitude(self) -> float:
        return math.hypot(self.x, self.y)

    def normalized(self) -> Vec2D:
        mag = self.magnitude
        if mag == 0:
            return Vec2D(0.0, 0.0)
        return Vec2D(self.x / mag, self.y / mag)

    def distance_to(self, other: Vec2D) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def rotated(self, angle_rad: float) -> Vec2D:
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        return Vec2D(
            self.x * cos_a - self.y * sin_a,
            self.x * sin_a + self.y * cos_a,
        )

    def to_tuple(self) -> tuple[float, float]:
        return (self.x, self.y)


@dataclass
class Segment2D:
    p1: Vec2D
    p2: Vec2D

    def length(self) -> float:
        return self.p1.distance_to(self.p2)

    def intersect_ray(self, ray_origin: Vec2D, ray_dir: Vec2D, max_range: float) -> Optional[float]:
        """Calculates distance from ray_origin along ray_dir to intersection with this segment."""
        # Ray: P = O + t * D (t >= 0, t <= max_range)
        # Segment: Q = A + u * (B - A) (0 <= u <= 1)
        v1 = ray_origin - self.p1
        v2 = self.p2 - self.p1
        v3 = Vec2D(-ray_dir.y, ray_dir.x)

        dot = v2.dot(v3)
        if abs(dot) < 1e-9:
            return None  # Parallel

        t1 = v2.cross(v1) / dot
        t2 = v1.dot(v3) / dot

        if t1 >= 0.0 and t1 <= max_range and 0.0 <= t2 <= 1.0:
            return t1
        return None


@dataclass
class Polygon2D:
    vertices: list[Vec2D]

    @classmethod
    def from_box(cls, center: Vec2D, width: float, length: float, heading: float = 0.0) -> Polygon2D:
        """Create oriented rectangle from center, width, length, and heading angle."""
        hw = width / 2.0
        hl = length / 2.0
        # Local unrotated corners (length along x, width along y)
        local_corners = [
            Vec2D(hl, hw),
            Vec2D(-hl, hw),
            Vec2D(-hl, -hw),
            Vec2D(hl, -hw),
        ]
        world_vertices = [center + c.rotated(heading) for c in local_corners]
        return cls(vertices=world_vertices)

    def get_edges(self) -> list[Segment2D]:
        edges = []
        n = len(self.vertices)
        for i in range(n):
            edges.append(Segment2D(self.vertices[i], self.vertices[(i + 1) % n]))
        return edges

    def get_normals(self) -> list[Vec2D]:
        """Get perpendicular normal vectors for SAT collision testing."""
        normals = []
        n = len(self.vertices)
        for i in range(n):
            edge = self.vertices[(i + 1) % n] - self.vertices[i]
            # Perpendicular vector
            normal = Vec2D(-edge.y, edge.x).normalized()
            normals.append(normal)
        return normals

    def project_onto_axis(self, axis: Vec2D) -> tuple[float, float]:
        """Project all vertices onto an axis and return (min_proj, max_proj)."""
        projections = [v.dot(axis) for v in self.vertices]
        return min(projections), max(projections)

    def intersects(self, other: Polygon2D) -> bool:
        """Separating Axis Theorem (SAT) convex polygon intersection test."""
        axes = self.get_normals() + other.get_normals()
        for axis in axes:
            min_a, max_a = self.project_onto_axis(axis)
            min_b, max_b = other.project_onto_axis(axis)
            # Check for separation gap
            if max_a < min_b or max_b < min_a:
                return False
        return True

    def raycast(self, ray_origin: Vec2D, ray_dir: Vec2D, max_range: float) -> Optional[float]:
        """Finds closest intersection distance of ray against all polygon edges."""
        min_dist: Optional[float] = None
        for edge in self.get_edges():
            dist = edge.intersect_ray(ray_origin, ray_dir, max_range)
            if dist is not None:
                if min_dist is None or dist < min_dist:
                    min_dist = dist
        return min_dist

    def min_distance_to_point(self, point: Vec2D) -> float:
        """Calculate minimum Euclidean distance from a point to polygon boundaries."""
        min_d = float("inf")
        for edge in self.get_edges():
            # Project point onto segment
            ab = edge.p2 - edge.p1
            ap = point - edge.p1
            ab_len_sq = ab.magnitude_sq
            if ab_len_sq == 0:
                d = point.distance_to(edge.p1)
            else:
                t = max(0.0, min(1.0, ap.dot(ab) / ab_len_sq))
                projection = edge.p1 + ab * t
                d = point.distance_to(projection)
            if d < min_d:
                min_d = d
        return min_d
