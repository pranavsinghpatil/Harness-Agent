"""Kinematic and dynamic vehicle models for autonomous ground agents (rovers)."""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from sandbox.world.geometry import Vec2D, Polygon2D


@dataclass
class VehicleState:
    """State vector of the ground vehicle in world and body coordinates."""
    position: Vec2D = field(default_factory=lambda: Vec2D(0.0, 0.0))
    heading: float = 0.0  # radians (0 = along +X axis)
    velocity: float = 0.0  # m/s (longitudinal speed)
    angular_velocity: float = 0.0  # rad/s (yaw rate)
    acceleration: float = 0.0  # m/s^2
    steer_angle: float = 0.0  # radians (wheel angle relative to chassis)

    def to_dict(self) -> dict[str, float]:
        return {
            "x": round(self.position.x, 4),
            "y": round(self.position.y, 4),
            "heading": round(self.heading, 4),
            "velocity": round(self.velocity, 4),
            "angular_velocity": round(self.angular_velocity, 4),
            "acceleration": round(self.acceleration, 4),
            "steer_angle": round(self.steer_angle, 4),
        }


@dataclass
class VehicleParams:
    """Physical characteristics and actuation constraints of the vehicle."""
    wheelbase: float = 1.2  # meters (L)
    width: float = 0.9  # meters
    length: float = 1.4  # meters
    mass: float = 40.0  # kg
    max_speed: float = 6.0  # m/s (~21.6 km/h)
    min_speed: float = -2.0  # m/s (reverse)
    max_acceleration: float = 3.0  # m/s^2
    max_brake_deceleration: float = 5.0  # m/s^2
    emergency_brake_deceleration: float = 8.0  # m/s^2
    max_steer_angle: float = 0.6  # rad (~34.3 degrees)
    max_steer_rate: float = 2.0  # rad/s
    drag_coefficient: float = 0.1  # air/rolling resistance damping


class KinematicVehicleModel:
    """Kinematic Bicycle Model with bounded acceleration, steering rates, and friction damping."""

    def __init__(self, params: VehicleParams | None = None) -> None:
        self.params = params or VehicleParams()
        self.state = VehicleState()

    def set_state(self, state: VehicleState) -> None:
        self.state = state

    def get_polygon(self) -> Polygon2D:
        """Returns the current oriented bounding box of the vehicle."""
        return Polygon2D.from_box(
            center=self.state.position,
            width=self.params.width,
            length=self.params.length,
            heading=self.state.heading,
        )

    def step(
        self,
        throttle: float,
        brake: float,
        steering_target: float,
        emergency_stop: bool,
        dt: float,
    ) -> VehicleState:
        """Integrates the vehicle motion forward by dt given actuator inputs."""
        if dt <= 0:
            return self.state

        # Clamping inputs
        throttle = max(0.0, min(1.0, throttle))
        brake = max(0.0, min(1.0, brake))
        steering_target = max(
            -self.params.max_steer_angle,
            min(self.params.max_steer_angle, steering_target),
        )

        # 1. Update steering angle with slew rate limiting
        steer_diff = steering_target - self.state.steer_angle
        max_steer_step = self.params.max_steer_rate * dt
        if abs(steer_diff) <= max_steer_step:
            self.state.steer_angle = steering_target
        else:
            self.state.steer_angle += math.copysign(max_steer_step, steer_diff)

        # 2. Compute net longitudinal acceleration
        if emergency_stop:
            if self.state.velocity > 0:
                net_accel = -self.params.emergency_brake_deceleration
            elif self.state.velocity < 0:
                net_accel = self.params.emergency_brake_deceleration
            else:
                net_accel = 0.0
        else:
            accel_cmd = throttle * self.params.max_acceleration
            # Braking opposes current velocity direction
            if self.state.velocity > 0:
                brake_cmd = brake * self.params.max_brake_deceleration
            elif self.state.velocity < 0:
                brake_cmd = -brake * self.params.max_brake_deceleration
            else:
                brake_cmd = 0.0

            drag = self.params.drag_coefficient * self.state.velocity
            net_accel = accel_cmd - brake_cmd - drag

        self.state.acceleration = net_accel

        # 3. Velocity integration
        new_v = self.state.velocity + net_accel * dt
        # When braking from moving, stop at zero without overshoot
        if self.state.velocity > 0 and new_v <= 0 and (brake > 0 or emergency_stop or throttle == 0):
            new_v = 0.0
            self.state.acceleration = 0.0
        elif self.state.velocity < 0 and new_v >= 0 and (brake > 0 or emergency_stop or throttle == 0):
            new_v = 0.0
            self.state.acceleration = 0.0
        elif abs(self.state.velocity) < 1e-4 and throttle == 0:
            new_v = 0.0
            self.state.acceleration = 0.0

        self.state.velocity = max(self.params.min_speed, min(self.params.max_speed, new_v))

        # 4. Angular velocity & heading integration (Kinematic Bicycle model)
        # yaw_rate = (v / L) * tan(delta)
        yaw_rate = (self.state.velocity / self.params.wheelbase) * math.tan(self.state.steer_angle)
        self.state.angular_velocity = yaw_rate

        new_heading = self.state.heading + yaw_rate * dt
        # Normalize heading to [-pi, pi]
        self.state.heading = (new_heading + math.pi) % (2 * math.pi) - math.pi

        # 5. Position integration
        dx = self.state.velocity * math.cos(self.state.heading) * dt
        dy = self.state.velocity * math.sin(self.state.heading) * dt
        self.state.position = self.state.position + Vec2D(dx, dy)

        return self.state
