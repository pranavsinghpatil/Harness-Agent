"""Master SandboxEnvironment coordinating all simulation subsystems, timing, and lifecycle."""

from __future__ import annotations
import math
import uuid
from typing import Any, Optional
from sandbox.core.clock import SimClock, EventQueue
from sandbox.core.rng import RngManager
from sandbox.core.episode import EpisodeLifecycle, EpisodeConfig, EpisodeStatus
from sandbox.world.geometry import Vec2D
from sandbox.world.entities import StaticObstacle, DynamicObstacle
from sandbox.world.map import WorldMap
from sandbox.physics.dynamics import VehicleState, VehicleParams
from sandbox.physics.engine import PhysicsEngine
from sandbox.sensors.base import BaseSensor
from sandbox.sensors.lidar import LidarSensor
from sandbox.sensors.imu import ImuSensor
from sandbox.sensors.encoder import EncoderSensor
from sandbox.sensors.position import PositionSensor
from sandbox.sensors.camera import CameraSensor
from sandbox.transport.bus import TransportBus
from sandbox.hardware.scheduler import VirtualEdgeScheduler
from sandbox.hardware.profile import ComputeTask
from sandbox.actuators.pipeline import ActuatorPipeline
from sandbox.actuators.command import ActuatorCommand
from sandbox.faults.controller import FaultController
from sandbox.safety.oracle import SafetyOracle
from sandbox.telemetry.recorder import TelemetryRecorder, TelemetryFrame
from sandbox.telemetry.manifest import RunManifest
from scenarios.schema import ScenarioDefinition
from target_agents.base import BaseTargetAgent
from target_agents.reference_agent.agent import ReferenceAutonomousAgent


class SandboxEnvironment:
    """The master simulation environment integrating physics, hardware, agent, and observability."""

    def __init__(
        self,
        scenario: ScenarioDefinition | None = None,
        target_agent: BaseTargetAgent | None = None,
        run_id: str | None = None,
    ) -> None:
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
        self.scenario = scenario
        self.target_agent = target_agent or ReferenceAutonomousAgent()

        # 1. Core
        seed = scenario.seed if scenario else 42
        self.rng_manager = RngManager(master_seed=seed)
        self.clock = SimClock()
        self.event_queue = EventQueue()

        # 2. Episode Config & Lifecycle
        max_time = scenario.max_sim_time if scenario else 30.0
        self.episode_config = EpisodeConfig(max_sim_time=max_time, seed=seed)
        self.lifecycle = EpisodeLifecycle(self.episode_config)

        # 3. World & Physics
        self.world_map = WorldMap()
        self.vehicle_params = VehicleParams()
        self.physics = PhysicsEngine(self.world_map, self.vehicle_params)

        # 4. Sensors
        self.sensors: dict[str, BaseSensor] = {
            "lidar": LidarSensor(rng=self.rng_manager.get("sensors")),
            "imu": ImuSensor(rng=self.rng_manager.get("sensors")),
            "encoder": EncoderSensor(rng=self.rng_manager.get("sensors")),
            "position": PositionSensor(rng=self.rng_manager.get("sensors")),
            "camera": CameraSensor(rng=self.rng_manager.get("sensors")),
        }

        # 5. Transport Bus
        self.transport = TransportBus(rng=self.rng_manager.get("transport"))
        self.transport.register_channel("sensor.lidar", base_latency_s=0.015, jitter_std_s=0.002)
        self.transport.register_channel("sensor.imu", base_latency_s=0.003, jitter_std_s=0.001)
        self.transport.register_channel("sensor.encoder", base_latency_s=0.003, jitter_std_s=0.001)
        self.transport.register_channel("sensor.position", base_latency_s=0.020, jitter_std_s=0.004)
        self.transport.register_channel("sensor.camera", base_latency_s=0.025, jitter_std_s=0.005)

        # 6. Virtual Edge Compute Scheduler
        self.hardware = VirtualEdgeScheduler()

        # 7. Actuator Pipeline
        self.actuators = ActuatorPipeline(rng=self.rng_manager.get("actuators"))

        # 8. Fault Controller
        self.faults = FaultController()

        # 9. Safety Oracle
        self.safety = SafetyOracle()

        # 10. Telemetry Recorder
        self.telemetry = TelemetryRecorder(run_id=self.run_id)

        # Apply scenario if provided
        if scenario:
            self.load_scenario(scenario)

    def load_scenario(self, scenario: ScenarioDefinition) -> None:
        """Configures world entities, goals, initial pose, and fault schedules from scenario."""
        self.scenario = scenario
        self.episode_config.max_sim_time = scenario.max_sim_time
        self.episode_config.seed = scenario.seed
        self.rng_manager.reset(scenario.seed)

        # Reset world map
        self.world_map = WorldMap(
            width=scenario.world.width,
            height=scenario.world.height,
            goal_position=Vec2D(scenario.world.goal[0], scenario.world.goal[1]),
        )
        self.physics = PhysicsEngine(self.world_map, self.vehicle_params)

        # Add obstacles
        for obs_spec in scenario.world.obstacles:
            if obs_spec.type == "dynamic":
                dyn_obs = DynamicObstacle(
                    id=obs_spec.id,
                    position=Vec2D(obs_spec.x, obs_spec.y),
                    heading=obs_spec.heading,
                    width=obs_spec.width,
                    length=obs_spec.length,
                    target_speed=obs_spec.target_speed,
                    waypoints=[Vec2D(wp[0], wp[1]) for wp in obs_spec.waypoints],
                )
                self.world_map.add_dynamic_obstacle(dyn_obs)
            else:
                static_obs = StaticObstacle(
                    id=obs_spec.id,
                    position=Vec2D(obs_spec.x, obs_spec.y),
                    heading=obs_spec.heading,
                    width=obs_spec.width,
                    length=obs_spec.length,
                )
                self.world_map.add_static_obstacle(static_obs)

        # Set initial vehicle state
        init_state = VehicleState(
            position=Vec2D(scenario.world.initial_state.x, scenario.world.initial_state.y),
            heading=scenario.world.initial_state.heading,
            velocity=scenario.world.initial_state.velocity,
        )
        self.physics.reset(init_state)

        # Set safety thresholds
        self.safety = SafetyOracle(
            min_clearance_threshold=scenario.safety_thresholds.get("min_clearance", 0.8),
            speed_limit=scenario.safety_thresholds.get("speed_limit", 6.5),
            max_observation_age_s=scenario.safety_thresholds.get("max_observation_age_s", 0.4),
        )

        # Set faults
        self.faults.set_faults(scenario.fault_schedule)

        # Reset target agent
        self.target_agent.reset(scenario.world.goal[0], scenario.world.goal[1])

    def reset(self) -> None:
        """Resets all simulation components to initial state."""
        self.clock.reset()
        self.event_queue.clear()
        self.lifecycle = EpisodeLifecycle(self.episode_config)
        self.lifecycle.start(self.clock.current_time)

        for sensor in self.sensors.values():
            sensor.reset()

        self.transport.reset()
        self.hardware.reset()
        self.actuators.reset()
        self.faults.reset()
        self.safety.reset()
        self.telemetry.reset(self.run_id)

        if self.scenario:
            self.load_scenario(self.scenario)

    def step(self, dt: float = 0.01) -> TelemetryFrame:
        """Executes a single simulation tick (default 100 Hz = 0.01s)."""
        sim_time = self.clock.advance_by(dt)

        # 1. Update and apply active faults
        active_fault_ids = self.faults.update(
            sim_time=sim_time,
            sensors=self.sensors,
            transport=self.transport,
            hardware=self.hardware,
            actuators=self.actuators,
        )

        # 2. Get latest applied command from actuator pipeline
        applied_command = self.actuators.step(sim_time)

        # 3. Physics step: dynamics & collision checks
        vehicle_state, collision_res = self.physics.step(
            throttle=applied_command.throttle,
            brake=applied_command.brake,
            steering=applied_command.steering,
            emergency_stop=applied_command.emergency_stop,
            dt=dt,
        )

        # 4. Generate sensor packets for due sensors & dispatch to transport bus
        for sensor_key, sensor in self.sensors.items():
            if sensor.should_sample(sim_time):
                packet = sensor.sample(sim_time, vehicle_state, self.world_map)
                if packet:
                    channel_name = f"sensor.{sensor_key}"
                    self.transport.send(channel_name, packet, sim_time)

        # 5. Deliver arrived sensor packets from transport bus
        delivered_by_channel = self.transport.deliver_all_due(sim_time)
        all_delivered_packets = []
        for packets in delivered_by_channel.values():
            all_delivered_packets.extend(packets)

        # 6. Virtual Edge Compute scheduler step
        self.hardware.step(sim_time, dt)

        # 7. Deliver observations to target agent
        if all_delivered_packets:
            self.target_agent.receive_sensor_packets(all_delivered_packets, sim_time)

        # 8. Agent control task execution (typically at 20 Hz, e.g. every 0.05s)
        agent_command = self.target_agent.step(sim_time)

        # 9. Submit agent command to actuator pipeline
        self.actuators.submit_command(agent_command, sim_time)

        # 10. Safety Oracle evaluation
        obs_age = 0.0
        if hasattr(self.target_agent, "perception"):
            obs_age = self.target_agent.perception.state.get_max_observation_age(sim_time)

        new_violations = self.safety.evaluate(
            sim_time=sim_time,
            state=vehicle_state,
            params=self.vehicle_params,
            collision_result=collision_res,
            current_command=applied_command,
            observation_age_s=obs_age,
        )

        # 11. Check Episode Termination Conditions
        dist_to_goal = vehicle_state.position.distance_to(self.world_map.goal_position)
        if dist_to_goal <= self.episode_config.goal_tolerance:
            self.lifecycle.finish(
                EpisodeStatus.GOAL_REACHED,
                f"Goal reached at ({self.world_map.goal_position.x}, {self.world_map.goal_position.y})",
                sim_time,
            )
        elif collision_res.is_collision and self.episode_config.terminate_on_collision:
            self.lifecycle.finish(
                EpisodeStatus.SAFETY_VIOLATION,
                f"Collision with {collision_res.collided_entity_id}",
                sim_time,
            )
        elif self.safety.has_fatal_violations and self.episode_config.terminate_on_safety_violation:
            self.lifecycle.finish(
                EpisodeStatus.SAFETY_VIOLATION,
                "Fatal safety rule violation detected by Safety Oracle",
                sim_time,
            )
        else:
            self.lifecycle.check_timeout(sim_time)

        # 12. Record Telemetry Frame
        queue_depths = {
            name: ch.in_flight_count for name, ch in self.transport.channels.items()
        }
        dyn_obs_data = [
            {
                "id": o.id,
                "x": round(o.position.x, 3),
                "y": round(o.position.y, 3),
                "heading": round(o.heading, 3),
                "velocity": round(o.velocity.magnitude, 3),
            }
            for o in self.world_map.dynamic_obstacles
            if o.is_active
        ]

        frame = TelemetryFrame(
            sim_time=round(sim_time, 4),
            step=self.clock.step_count,
            vehicle_state=vehicle_state.to_dict(),
            actuator_command=applied_command.to_dict(),
            min_clearance=round(collision_res.min_clearance, 3),
            active_faults=active_fault_ids,
            sensor_queue_depths=queue_depths,
            hardware_metrics={
                "cpu_utilization": self.hardware.metrics.cpu_utilization,
                "temperature_celsius": self.hardware.metrics.temperature_celsius,
                "is_throttled": self.hardware.metrics.is_throttled,
                "queue_depth": self.hardware.metrics.queue_depth,
                "deadline_misses": self.hardware.metrics.total_deadline_misses,
            },
            dynamic_obstacles=dyn_obs_data,
            new_violations=[v.to_dict() for v in new_violations],
        )

        self.telemetry.record_frame(frame)
        return frame

    def run_episode(self, max_sim_time: float | None = None) -> tuple[RunManifest, list[TelemetryFrame]]:
        """Runs the entire episode to completion."""
        self.reset()
        if max_sim_time:
            self.episode_config.max_sim_time = max_sim_time

        dt = self.episode_config.fixed_dt

        while not self.lifecycle.is_finished:
            self.step(dt)

        # Build final RunManifest
        manifest = RunManifest(
            run_id=self.run_id,
            seed=self.episode_config.seed,
            scenario_id=self.scenario.id if self.scenario else "ad_hoc",
            target_agent_version=getattr(self.target_agent, "agent_id", "custom"),
            fault_ids=[f.id for f in self.scenario.fault_schedule] if self.scenario else [],
            status=self.lifecycle.status.value,
            termination_reason=self.lifecycle.termination_reason,
            sim_duration_seconds=round(self.clock.current_time, 3),
            total_steps=self.clock.step_count,
            violations_count=self.safety.total_violations,
            trace_hash=self.telemetry.compute_trace_hash(),
        )

        return manifest, self.telemetry.frames
