"""PID speed controller and steering tracking."""

from __future__ import annotations
from sandbox.actuators.command import ActuatorCommand
from target_agents.reference_agent.state_estimator import EstimatedPose
from target_agents.reference_agent.planner import PlanTarget


class PIDController:
    """PID speed and tracking controller outputting throttle, brake, and steering."""

    def __init__(
        self,
        kp_speed: float = 0.6,
        ki_speed: float = 0.05,
        kd_speed: float = 0.02,
    ) -> None:
        self.kp_speed = kp_speed
        self.ki_speed = ki_speed
        self.kd_speed = kd_speed
        self.speed_error_integral: float = 0.0
        self.last_speed_error: float = 0.0

    def reset(self) -> None:
        self.speed_error_integral = 0.0
        self.last_speed_error = 0.0

    def compute_command(
        self,
        pose: EstimatedPose,
        plan: PlanTarget,
        dt: float = 0.05,
    ) -> ActuatorCommand:
        if plan.is_emergency:
            return ActuatorCommand(
                throttle=0.0,
                brake=1.0,
                steering=plan.target_steering,
                emergency_stop=True,
            )

        speed_err = plan.target_speed - pose.speed
        self.speed_error_integral = max(-5.0, min(5.0, self.speed_error_integral + speed_err * dt))
        speed_derivative = (speed_err - self.last_speed_error) / max(1e-5, dt)
        self.last_speed_error = speed_err

        control_output = (
            self.kp_speed * speed_err
            + self.ki_speed * self.speed_error_integral
            + self.kd_speed * speed_derivative
        )

        if control_output > 0:
            throttle = max(0.0, min(1.0, control_output))
            brake = 0.0
        else:
            throttle = 0.0
            brake = max(0.0, min(1.0, -control_output))

        return ActuatorCommand(
            throttle=round(throttle, 3),
            brake=round(brake, 3),
            steering=round(plan.target_steering, 3),
            emergency_stop=False,
        )
