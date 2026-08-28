"""Complete reference autonomous ground agent combining perception, estimation, planning, and control."""

from __future__ import annotations
from sandbox.sensors.packet import SensorPacket
from sandbox.actuators.command import ActuatorCommand
from target_agents.base import BaseTargetAgent
from target_agents.reference_agent.perception import PerceptionAggregator
from target_agents.reference_agent.state_estimator import StateEstimator
from target_agents.reference_agent.planner import MotionPlanner
from target_agents.reference_agent.controller import PIDController


class ReferenceAutonomousAgent(BaseTargetAgent):
    """Full-stack autonomous ground agent operating over simulated hardware interfaces."""

    def __init__(
        self,
        agent_id: str = "reference_ground_agent_v1",
        cruising_speed: float = 4.0,
        safe_stopping_distance: float = 7.0,
        emergency_distance: float = 3.0,
    ) -> None:
        super().__init__(agent_id=agent_id)
        self.perception = PerceptionAggregator()
        self.estimator = StateEstimator()
        self.planner = MotionPlanner(
            cruising_speed=cruising_speed,
            safe_stopping_distance=safe_stopping_distance,
            emergency_distance=emergency_distance,
        )
        self.controller = PIDController()
        self.last_step_time: float = 0.0

    def reset(
        self,
        goal_x: float,
        goal_y: float,
        initial_x: float = 0.0,
        initial_y: float = 0.0,
        initial_heading: float = 0.0,
    ) -> None:
        self.perception.reset()
        self.estimator.reset(initial_x=initial_x, initial_y=initial_y, initial_heading=initial_heading)
        self.planner.set_goal(goal_x, goal_y)
        self.controller.reset()
        self.last_step_time = 0.0

    def receive_sensor_packets(self, packets: list[SensorPacket], current_sim_time: float) -> None:
        self.perception.update(packets, current_sim_time)

    def step(self, current_sim_time: float) -> ActuatorCommand:
        dt = (
            current_sim_time - self.last_step_time
            if self.last_step_time > 0
            else 0.05
        )
        self.last_step_time = current_sim_time

        # 1. State Estimation
        pose = self.estimator.update(self.perception.state, dt)

        # 2. Path & Velocity Planning
        plan = self.planner.plan(pose, self.perception.state)

        # 3. Control Command Generation
        command = self.controller.compute_command(pose, plan, dt)

        return command
