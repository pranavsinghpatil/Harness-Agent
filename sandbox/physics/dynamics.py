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

    def _update_steering(self, steering_target: float, dt: float) -> None:
        """Updates vehicle wheel steer angle subject to steering limits and slew rate."""
        clamped_target = max(-self.params.max_steer_angle, min(self.params.max_steer_angle, steering_target))
        steer_diff = clamped_target - self.state.steer_angle
        max_steer_step = self.params.max_steer_rate * dt
        if abs(steer_diff) <= max_steer_step:
            self.state.steer_angle = clamped_target
        else:
            self.state.steer_angle += math.copysign(max_steer_step, steer_diff)

    def _compute_longitudinal_acceleration(self, throttle: float, brake: float, emergency_stop: bool) -> float:
        """Computes net longitudinal acceleration considering drive forces, braking, and drag."""
        if emergency_stop:
            if self.state.velocity > 0:
                return -self.params.emergency_brake_deceleration
            elif self.state.velocity < 0:
                return self.params.emergency_brake_deceleration
            return 0.0

        accel_cmd = throttle * self.params.max_acceleration
        if self.state.velocity > 0:
            brake_cmd = brake * self.params.max_brake_deceleration
        elif self.state.velocity < 0:
            brake_cmd = -brake * self.params.max_brake_deceleration
        else:
            brake_cmd = 0.0

        drag = self.params.drag_coefficient * self.state.velocity
        return accel_cmd - brake_cmd - drag

    def _integrate_velocity(self, net_accel: float, throttle: float, brake: float, emergency_stop: bool, dt: float) -> None:
        """Integrates vehicle velocity and clamps within speed and zero-crossing boundaries."""
        self.state.acceleration = net_accel
        new_v = self.state.velocity + net_accel * dt

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

    def _integrate_pose(self, dt: float) -> None:
        """Integrates heading and Cartesian position from kinematic bicycle formulas."""
        yaw_rate = (self.state.velocity / self.params.wheelbase) * math.tan(self.state.steer_angle)
        self.state.angular_velocity = yaw_rate

        new_heading = self.state.heading + yaw_rate * dt
        self.state.heading = (new_heading + math.pi) % (2 * math.pi) - math.pi

        dx = self.state.velocity * math.cos(self.state.heading) * dt
        dy = self.state.velocity * math.sin(self.state.heading) * dt
        self.state.position = self.state.position + Vec2D(dx, dy)

    def step(
        self,
        throttle: float,
        brake: float,
        steering_target: float,
        emergency_stop: bool,
        dt: float,
    ) -> VehicleState:
        """Integrates vehicle state forward by dt using kinematic bicycle dynamics.

        Args:
            throttle: Normalized throttle command in range [0.0, 1.0].
            brake: Normalized brake command in range [0.0, 1.0].
            steering_target: Desired wheel steer angle in radians [-max_steer, +max_steer].
            emergency_stop: Boolean flag to immediately engage maximum emergency braking.
            dt: Discrete simulation timestep in seconds (must be strictly positive).

        Returns:
            VehicleState: Mutated reference to vehicle state after integration.
        """
        if dt <= 0:
            return self.state

        clamped_throttle = max(0.0, min(1.0, throttle))
        clamped_brake = max(0.0, min(1.0, brake))

        self._update_steering(steering_target, dt)
        net_accel = self._compute_longitudinal_acceleration(clamped_throttle, clamped_brake, emergency_stop)
        self._integrate_velocity(net_accel, clamped_throttle, clamped_brake, emergency_stop, dt)
        self._integrate_pose(dt)

        return self.state
