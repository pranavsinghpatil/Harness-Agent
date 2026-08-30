"""Master SandboxEnvironment coordinating all simulation subsystems, timing, and lifecycle."""

from __future__ import annotations
import math
import uuid
from typing import Any, Callable, Dict, List, Optional
from sandbox.core.clock import SimClock, EventQueue
from sandbox.core.rng import RngManager
from sandbox.core.episode import EpisodeLifecycle, EpisodeConfig, EpisodeStatus
from sandbox.world.geometry import Vec2D
from sandbox.world.entities import StaticObstacle, DynamicObstacle
from sandbox.world.map import WorldMap
from sandbox.physics.dynamics import VehicleState, VehicleParams
from sandbox.physics.engine import PhysicsEngine
from sandbox.physics.collision import CollisionResult
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
from sandbox.safety.oracle import SafetyOracle, SafetyViolation
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
        event_listener: Optional[Callable[[str, str, str, Dict[str, Any]], None]] = None,
    ) -> None:
        self.run_id = run_id or f"run_{uuid.uuid4().hex[:8]}"
        self.scenario = scenario
        self.target_agent = target_agent or ReferenceAutonomousAgent()
        self.event_listener = event_listener

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

        self._prev_deadline_misses: int = 0
        self._prev_fault_ids: set[str] = set()

        if scenario:
            self.load_scenario(scenario)

    def _emit(self, source: str, event_type: str, severity: str, payload: Dict[str, Any]) -> None:
        """Internal dispatch to registered event listener."""
        if self.event_listener:
            try:
                self.event_listener(source, event_type, severity, payload)
            except Exception:
                pass

    def _refresh_rng_bindings(self) -> None:
        """Re-binds fresh seed-isolated RNG generators to all sensors, transport, and actuators."""
        sensor_rng = self.rng_manager.get("sensors")
        for sensor in self.sensors.values():
            sensor.rng = sensor_rng

        self.transport.rng = self.rng_manager.get("transport")
        for channel in self.transport.channels.values():
            channel.rng = self.transport.rng

        self.actuators.rng = self.rng_manager.get("actuators")

    def load_scenario(self, scenario: ScenarioDefinition) -> None:
        """Configures world entities, goals, initial pose, and fault schedules from scenario.

        Args:
            scenario: The ScenarioDefinition model containing world, obstacles, and faults.

        Returns:
            None: Mutates environment world map, physics, safety oracle, and fault controller in place.

        Raises:
            KeyError: If mandatory scenario fields or initial state keys are missing.
        """
        self.scenario = scenario
        self.episode_config.max_sim_time = scenario.max_sim_time
        self.episode_config.seed = scenario.seed
        self.rng_manager.reset(scenario.seed)
        self._refresh_rng_bindings()

        self.world_map = WorldMap(
            width=scenario.world.width,
            height=scenario.world.height,
            goal_position=Vec2D(scenario.world.goal[0], scenario.world.goal[1]),
        )
        self.physics = PhysicsEngine(self.world_map, self.vehicle_params)

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

        init_state = VehicleState(
            position=Vec2D(scenario.world.initial_state.x, scenario.world.initial_state.y),
            heading=scenario.world.initial_state.heading,
            velocity=scenario.world.initial_state.velocity,
        )
        self.physics.reset(init_state)

        self.safety = SafetyOracle(
            min_clearance_threshold=scenario.safety_thresholds.get("min_clearance", 0.8),
            speed_limit=scenario.safety_thresholds.get("speed_limit", 6.5),
            max_observation_age_s=scenario.safety_thresholds.get("max_observation_age_s", 0.4),
        )

        self.faults.clear_active_faults(self.sensors, self.transport, self.hardware, self.actuators)
        self.faults.set_faults(scenario.fault_schedule)

        self.target_agent.reset(
            scenario.world.goal[0],
            scenario.world.goal[1],
            scenario.world.initial_state.x,
            scenario.world.initial_state.y,
            scenario.world.initial_state.heading,
        )

    def reset(self) -> None:
        """Resets all simulation components, clocks, queues, and sensors to initial state."""
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
        self._prev_deadline_misses = 0
        self._prev_fault_ids = set()

        if self.scenario:
            self.load_scenario(self.scenario)

    def _sample_and_deliver_sensors(self, sim_time: float, vehicle_state: VehicleState) -> list[Any]:
        """Samples active sensors and routes observations through the hardware transport bus."""
        for sensor_key, sensor in self.sensors.items():
            if sensor.should_sample(sim_time):
                packet = sensor.sample(sim_time, vehicle_state, self.world_map)
                if packet:
                    ch_name = f"sensor.{sensor_key}"
                    sent = self.transport.send(ch_name, packet, sim_time)
                    if sent:
                        self._emit(
                            f"sensors.{sensor_key}",
                            "SENSOR_SAMPLED",
                            "INFO",
                            {"channel": ch_name, "seq_id": getattr(packet, "sequence_id", 0), "timestamp": sim_time},
                        )
                    else:
                        self._emit(
                            f"transport.{sensor_key}",
                            "PACKET_DROPPED",
                            "WARNING",
                            {"channel": ch_name, "reason": "buffer_overflow_or_loss"},
                        )

        delivered_by_channel = self.transport.deliver_all_due(sim_time)
        all_delivered: list[Any] = []
        for ch_name, packets in delivered_by_channel.items():
            all_delivered.extend(packets)
            if packets:
                self._emit(
                    f"transport.{ch_name}",
                    "PACKET_DELIVERED",
                    "INFO",
                    {"channel": ch_name, "packet_count": len(packets)},
                )
        return all_delivered

    def _emit_compute_task(self, event_type: str, task: ComputeTask, sim_time: float) -> None:
        """Publish scheduler provenance for one queued, started, or completed task."""
        self._emit(
            "hardware.scheduler",
            event_type,
            "INFO",
            {
                "task_id": task.task_id,
                "name": task.name,
                "compute_cost_units": task.compute_cost_units,
                "input_timestamp": task.input_timestamp,
                "deadline": task.deadline,
                "timestamp": sim_time,
                "started_at": task.started_at,
                "completed_at": task.completed_at,
            },
        )

    def _check_termination(self, sim_time: float, vehicle_state: VehicleState, collision_res: CollisionResult) -> None:
        """Evaluates goal completion, collision termination, or timeout lifecycle triggers."""
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
            self._emit(
                "physics.collision",
                "COLLISION_DETECTED",
                "CRITICAL",
                {"obstacle_id": collision_res.collided_entity_id, "clearance": collision_res.min_clearance},
            )
        elif self.safety.has_fatal_violations and self.episode_config.terminate_on_safety_violation:
            self.lifecycle.finish(
                EpisodeStatus.SAFETY_VIOLATION,
                "Fatal safety rule violation detected by Safety Oracle",
                sim_time,
            )
        else:
            self.lifecycle.check_timeout(sim_time)

    def _record_telemetry_frame(
        self,
        sim_time: float,
        vehicle_state: VehicleState,
        applied_command: ActuatorCommand,
        collision_res: CollisionResult,
        active_fault_ids: list[str],
        new_violations: list[SafetyViolation],
    ) -> TelemetryFrame:
        """Constructs and stores a high-rate TelemetryFrame."""
        queue_depths = {name: ch.in_flight_count for name, ch in self.transport.channels.items()}
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

    def step(self, dt: float = 0.01) -> TelemetryFrame:
        """Executes a single simulation tick (default 100 Hz = 0.01s).

        Args:
            dt: Timestep duration in seconds (must be positive).

        Returns:
            TelemetryFrame: Recorded snapshot of the simulation step.
        """
        sim_time = self.clock.advance_by(dt)

        active_faults = self.faults.update(sim_time, self.sensors, self.transport, self.hardware, self.actuators)
        active_set = set(active_faults)
        newly_active = active_set - self._prev_fault_ids
        for f_id in newly_active:
            self._emit("faults.controller", "FAULT_INJECTED", "WARNING", {"fault_id": f_id, "sim_time": sim_time})
        self._prev_fault_ids = active_set

        applied_cmd = self.actuators.step(sim_time)
        if applied_cmd.command_id > 0:
            self._emit(
                "actuator.pipeline",
                "ACTUATOR_APPLIED",
                "INFO",
                {
                    "command_id": applied_cmd.command_id,
                    "timestamp": sim_time,
                    "throttle": applied_cmd.throttle,
                    "brake": applied_cmd.brake,
                    "steering": applied_cmd.steering,
                },
            )
        v_state, col_res = self.physics.step(
            applied_cmd.throttle, applied_cmd.brake, applied_cmd.steering, applied_cmd.emergency_stop, dt
        )

        delivered_packets = self._sample_and_deliver_sensors(sim_time, v_state)
        if delivered_packets:
            self.target_agent.receive_sensor_packets(delivered_packets, sim_time)
            perception_task = ComputeTask(
                task_id=f"compute_perception_{self.clock.step_count}",
                name="perception",
                compute_cost_units=0.1,
                deadline=sim_time + dt,
                priority=5,
                input_timestamp=sim_time,
                result_payload={"packet_count": len(delivered_packets)},
            )
            if self.hardware.submit_task(perception_task):
                self._emit_compute_task("TASK_SCHEDULED", perception_task, sim_time)

        controller_task = ComputeTask(
            task_id=f"compute_controller_{self.clock.step_count}",
            name="controller",
            compute_cost_units=0.1,
            deadline=sim_time + dt,
            priority=10,
            input_timestamp=sim_time,
        )
        controller_queued = self.hardware.submit_task(controller_task)
        if controller_queued:
            self._emit_compute_task("TASK_SCHEDULED", controller_task, sim_time)

        self.hardware.step(sim_time, dt)
        for task in self.hardware.started_tasks:
            self._emit_compute_task("COMPUTE_STARTED", task, task.started_at or sim_time)
        for task in self.hardware.completed_tasks_this_step:
            self._emit_compute_task("TASK_COMPLETED", task, task.completed_at or sim_time)

        # Emit hardware scheduler events
        if self.hardware.metrics.is_throttled:
            self._emit(
                "hardware.thermal",
                "THERMAL_THROTTLED",
                "WARNING",
                {"temperature_celsius": self.hardware.metrics.temperature_celsius},
            )
        if self.hardware.metrics.total_deadline_misses > self._prev_deadline_misses:
            delta = self.hardware.metrics.total_deadline_misses - self._prev_deadline_misses
            self._prev_deadline_misses = self.hardware.metrics.total_deadline_misses
            self._emit(
                "hardware.scheduler",
                "DEADLINE_MISSED",
                "ERROR",
                {"misses_delta": delta, "total_misses": self.hardware.metrics.total_deadline_misses},
            )

        if controller_task.is_completed:
            agent_cmd = self.target_agent.step(sim_time)
            submitted = self.actuators.submit_command(agent_cmd, sim_time)
            self._emit(
                "agent.controller",
                "COMMAND_ISSUED",
                "INFO",
                {
                    "accepted": submitted,
                    "command_id": agent_cmd.command_id,
                    "input_timestamp": controller_task.input_timestamp,
                    "compute_started_at": controller_task.started_at,
                    "compute_completed_at": controller_task.completed_at,
                    "throttle": agent_cmd.throttle,
                    "brake": agent_cmd.brake,
                    "steering": agent_cmd.steering,
                },
            )
        else:
            self._emit(
                "agent.controller",
                "DEADLINE_MISSED",
                "ERROR",
                {
                    "task_id": controller_task.task_id,
                    "deadline": controller_task.deadline,
                    "timestamp": sim_time,
                    "reason": "controller compute did not complete",
                },
            )

        obs_age = 0.0
        if hasattr(self.target_agent, "perception"):
            obs_age = self.target_agent.perception.state.get_max_observation_age(sim_time)

        violations = self.safety.evaluate(sim_time, v_state, self.vehicle_params, col_res, applied_cmd, obs_age)
        for v in violations:
            self._emit(
                "safety.oracle",
                "INVARIANT_BREACHED",
                "CRITICAL",
                {"rule_name": v.rule_name, "severity": str(v.severity), "details": v.details},
            )

        self._check_termination(sim_time, v_state, col_res)
        return self._record_telemetry_frame(sim_time, v_state, applied_cmd, col_res, active_faults, violations)

    def run_episode(self, max_sim_time: float | None = None) -> tuple[RunManifest, list[TelemetryFrame]]:
        """Runs the entire episode to completion and produces the RunManifest.

        Args:
            max_sim_time: Optional upper bound on simulation time in seconds.

        Returns:
            tuple[RunManifest, list[TelemetryFrame]]: Tuple containing final manifest and all recorded frames.
        """
        self.reset()
        if max_sim_time:
            self.episode_config.max_sim_time = max_sim_time

        dt = self.episode_config.fixed_dt
        while not self.lifecycle.is_finished:
            self.step(dt)

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
