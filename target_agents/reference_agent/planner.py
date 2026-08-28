"""Motion planning and obstacle clearance evaluation."""

from __future__ import annotations
import math
from dataclasses import dataclass
from target_agents.reference_agent.perception import PerceptionState
from target_agents.reference_agent.state_estimator import EstimatedPose


@dataclass
class PlanTarget:
    target_speed: float
    target_steering: float
    is_emergency: bool
    distance_to_goal: float
    closest_obstacle_dist: float


class MotionPlanner:
    """Computes target velocity profile and steering angles based on path and obstacles."""

    def __init__(
        self,
        cruising_speed: float = 4.0,  # m/s
        safe_stopping_distance: float = 7.0,  # meters
        emergency_distance: float = 3.0,  # meters
    ) -> None:
        self.cruising_speed = cruising_speed
        self.safe_stopping_distance = safe_stopping_distance
        self.emergency_distance = emergency_distance
        self.goal_x: float = 0.0
        self.goal_y: float = 0.0

    def set_goal(self, goal_x: float, goal_y: float) -> None:
        self.goal_x = goal_x
        self.goal_y = goal_y

    def plan(self, pose: EstimatedPose, p_state: PerceptionState) -> PlanTarget:
        dx = self.goal_x - pose.x
        dy = self.goal_y - pose.y
        dist_to_goal = math.hypot(dx, dy)

        # 1. Determine obstacle clearance from LiDAR & Camera
        min_camera_dist = float("inf")
        for det in p_state.latest_camera_detections:
            if det.get("confidence", 0) > 0.4:
                d = det.get("distance", float("inf"))
                if d < min_camera_dist:
                    min_camera_dist = d

        closest_obs = min(p_state.latest_lidar_min_range, min_camera_dist)

        # 2. Speed Planning
        is_emergency = False
        if dist_to_goal < 0.5:
            target_speed = 0.0
        elif closest_obs <= self.emergency_distance:
            target_speed = 0.0
            is_emergency = True
        elif closest_obs < self.safe_stopping_distance:
            # Linear deceleration curve
            scale = (closest_obs - self.emergency_distance) / max(0.1, (self.safe_stopping_distance - self.emergency_distance))
            target_speed = self.cruising_speed * max(0.0, min(1.0, scale))
        else:
            target_speed = self.cruising_speed

        # 3. Steering Planning
        target_heading = math.atan2(dy, dx)
        heading_err = (target_heading - pose.heading + math.pi) % (2 * math.pi) - math.pi
        target_steering = max(-0.5, min(0.5, heading_err * 0.8))

        return PlanTarget(
            target_speed=target_speed,
            target_steering=target_steering,
            is_emergency=is_emergency,
            distance_to_goal=dist_to_goal,
            closest_obstacle_dist=closest_obs,
        )
