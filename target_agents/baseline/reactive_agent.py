"""Simple reactive baseline agent using raw sensor inputs without fusion."""

from __future__ import annotations
import math
from sandbox.sensors.packet import SensorPacket
from sandbox.actuators.command import ActuatorCommand
from target_agents.base import BaseTargetAgent


class ReactiveBaselineAgent(BaseTargetAgent):
    """Simple baseline rover agent with threshold-based braking."""

    def __init__(self, agent_id: str = "baseline_reactive") -> None:
        super().__init__(agent_id=agent_id)
        self.goal_x: float = 0.0
        self.goal_y: float = 0.0
        self.latest_closest_range: float = float("inf")
        self.latest_pos_x: float = 0.0
        self.latest_pos_y: float = 0.0
        self.latest_heading: float = 0.0
        self.last_sensor_time: float = 0.0

    def reset(self, goal_x: float, goal_y: float) -> None:
        self.goal_x = goal_x
        self.goal_y = goal_y
        self.latest_closest_range = float("inf")
        self.latest_pos_x = 0.0
        self.latest_pos_y = 0.0
        self.latest_heading = 0.0
        self.last_sensor_time = 0.0

    def receive_sensor_packets(self, packets: list[SensorPacket], current_sim_time: float) -> None:
        for p in packets:
            if not p.validity:
                continue
            if p.sensor_id == "sensor.lidar":
                self.latest_closest_range = p.payload.get("closest_range", float("inf"))
                self.last_sensor_time = p.measurement_timestamp
            elif p.sensor_id == "sensor.position":
                self.latest_pos_x = p.payload.get("x", self.latest_pos_x)
                self.latest_pos_y = p.payload.get("y", self.latest_pos_y)
                self.latest_heading = p.payload.get("heading", self.latest_heading)

    def step(self, current_sim_time: float) -> ActuatorCommand:
        # Emergency stop if obstacle within 2.0 meters
        if self.latest_closest_range < 2.0:
            return ActuatorCommand(throttle=0.0, brake=1.0, steering=0.0, emergency_stop=True)

        # Brake progressively if obstacle within 5.0 meters
        if self.latest_closest_range < 5.0:
            return ActuatorCommand(throttle=0.0, brake=0.8, steering=0.0, emergency_stop=False)

        # Steer toward goal
        dx = self.goal_x - self.latest_pos_x
        dy = self.goal_y - self.latest_pos_y
        target_angle = math.atan2(dy, dx)
        angle_diff = (target_angle - self.latest_heading + math.pi) % (2 * math.pi) - math.pi
        steer_cmd = max(-0.5, min(0.5, angle_diff * 0.8))

        dist_to_goal = math.hypot(dx, dy)
        if dist_to_goal < 0.5:
            return ActuatorCommand(throttle=0.0, brake=1.0, steering=0.0)

        return ActuatorCommand(throttle=0.6, brake=0.0, steering=steer_cmd)
