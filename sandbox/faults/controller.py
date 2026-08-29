"""Fault injection controller executing scheduled perturbations across system boundaries."""

from __future__ import annotations
from typing import Any, Optional
from sandbox.faults.schema import FaultDefinition
from sandbox.sensors.base import BaseSensor
from sandbox.sensors.lidar import LidarSensor
from sandbox.sensors.camera import CameraSensor
from sandbox.sensors.position import PositionSensor
from sandbox.transport.bus import TransportBus
from sandbox.hardware.scheduler import VirtualEdgeScheduler
from sandbox.hardware.profile import ComputeTask
from sandbox.actuators.pipeline import ActuatorPipeline


class FaultController:
    """Orchestrates scheduled declarative perturbations during an episode."""

    def __init__(self) -> None:
        self.scheduled_faults: list[FaultDefinition] = []
        self._active_fault_ids: set[str] = set()

    def add_fault(self, fault: FaultDefinition) -> None:
        self.scheduled_faults.append(fault)

    def set_faults(self, faults: list[FaultDefinition]) -> None:
        self.scheduled_faults = list(faults)

    def clear_active_faults(
        self,
        sensors: dict[str, BaseSensor],
        transport: TransportBus,
        hardware: VirtualEdgeScheduler,
        actuators: ActuatorPipeline,
    ) -> None:
        """Revert active state before discarding the schedule that created it."""
        active_faults: list[FaultDefinition] = [
            fault for fault in self.scheduled_faults if fault.id in self._active_fault_ids
        ]
        for fault in active_faults:
            self._revert_fault(fault, sensors, transport, hardware, actuators)
        self._active_fault_ids.clear()

    def get_active_fault_ids(self) -> list[str]:
        return sorted(list(self._active_fault_ids))

    def update(
        self,
        sim_time: float,
        sensors: dict[str, BaseSensor],
        transport: TransportBus,
        hardware: VirtualEdgeScheduler,
        actuators: ActuatorPipeline,
    ) -> list[str]:
        """Evaluates and applies active faults at current simulation time."""
        current_active_ids: set[str] = set()
        active_fault_objs: list[FaultDefinition] = []

        for fault in self.scheduled_faults:
            if fault.is_active_at(sim_time):
                current_active_ids.add(fault.id)
                active_fault_objs.append(fault)

        # Deactivations: faults that were active previously but ended
        for fault in self.scheduled_faults:
            if fault.id in self._active_fault_ids and fault.id not in current_active_ids:
                self._revert_fault(fault, sensors, transport, hardware, actuators)
                # Re-apply any other faults that are still active on the same target
                for remaining in active_fault_objs:
                    if remaining.target == fault.target:
                        self._apply_fault(remaining, sensors, transport, hardware, actuators, sim_time)

        # Activations: faults that just started
        for fault in active_fault_objs:
            if fault.id not in self._active_fault_ids:
                self._apply_fault(fault, sensors, transport, hardware, actuators, sim_time)

        self._active_fault_ids = current_active_ids
        return list(self._active_fault_ids)

    def _apply_sensor_fault(self, target: str, ftype: str, params: dict[str, Any], sensors: dict[str, BaseSensor]) -> None:
        sensor_key: str = target.replace("sensor.", "")
        sensor: Optional[BaseSensor] = sensors.get(sensor_key)
        if not sensor:
            return

        if ftype == "dropout":
            sensor.dropout_active = True
        elif ftype == "freeze":
            sensor.is_frozen = True
        elif ftype == "noise_burst":
            sensor.noise_scale = params.get("scale", 5.0)
        elif ftype == "bias_offset":
            sensor.bias_offset = params.get("offset", 1.0)
        elif ftype == "sector_loss" and isinstance(sensor, LidarSensor):
            min_a = params.get("min_angle_rad", -0.5)
            max_a = params.get("max_angle_rad", 0.5)
            sensor.dropped_sectors.append((min_a, max_a))
        elif ftype == "phantom_returns" and isinstance(sensor, LidarSensor):
            sensor.phantom_return_rate = params.get("rate", 0.3)
        elif ftype == "occlusion" and isinstance(sensor, CameraSensor):
            sensor.is_occluded = True
        elif ftype == "frame_drop" and isinstance(sensor, CameraSensor):
            sensor.frame_drop_rate = params.get("rate", 0.8)
        elif ftype == "confidence_degradation" and isinstance(sensor, CameraSensor):
            sensor.confidence_degradation = params.get("degradation", 0.4)
        elif ftype == "position_jump" and isinstance(sensor, PositionSensor):
            sensor.trigger_jump(params.get("offset_x", 3.0), params.get("offset_y", 3.0))

    def _apply_transport_fault(self, target: str, ftype: str, params: dict[str, Any], transport: TransportBus) -> None:
        channel_name = target.replace("transport.", "sensor.")
        channel = transport.get_channel(channel_name)
        if ftype == "added_latency":
            added_s = params.get("latency_ms", 300.0) / 1000.0
            channel.base_latency_s += added_s
        elif ftype == "packet_loss":
            channel.packet_loss_rate = params.get("loss_rate", 0.5)
        elif ftype == "jitter":
            channel.jitter_std_s = params.get("jitter_ms", 50.0) / 1000.0

    def _apply_compute_fault(self, ftype: str, params: dict[str, Any], hardware: VirtualEdgeScheduler, sim_time: float, fault_id: str) -> None:
        if ftype == "overload":
            task = ComputeTask(
                task_id=f"fault_overload_{fault_id}",
                name="overload_payload",
                compute_cost_units=params.get("compute_units", 200.0),
                deadline=sim_time + 0.1,
                priority=1,
                input_timestamp=sim_time,
            )
            hardware.submit_task(task)
        elif ftype == "cpu_availability":
            hardware.profile.cpu_availability_ratio = max(
                0.0, min(1.0, float(params.get("factor", 1.0)))
            )
        elif ftype == "thermal_spike":
            hardware.profile.current_temperature += params.get("temp_increase", 40.0)

    def _apply_actuator_fault(self, target: str, ftype: str, params: dict[str, Any], actuators: ActuatorPipeline) -> None:
        actuator_type = target.replace("actuator.", "")
        if actuator_type == "brake":
            if ftype == "reduced_effectiveness":
                actuators.brake_effectiveness_factor = params.get("factor", 0.3)
            elif ftype == "extra_delay":
                actuators.extra_delay_s += params.get("delay_ms", 200.0) / 1000.0
            elif ftype == "dropped_command":
                actuators.dropped_command_prob = params.get("drop_prob", 0.8)
        elif actuator_type == "steering":
            if ftype == "stuck_value":
                actuators.stuck_steering_angle = params.get("angle_rad", 0.4)
            elif ftype == "extra_delay":
                actuators.extra_delay_s += params.get("delay_ms", 200.0) / 1000.0
        elif actuator_type == "throttle":
            if ftype == "reduced_effectiveness":
                actuators.throttle_effectiveness_factor = params.get("factor", 0.3)

    def _apply_fault(
        self,
        fault: FaultDefinition,
        sensors: dict[str, BaseSensor],
        transport: TransportBus,
        hardware: VirtualEdgeScheduler,
        actuators: ActuatorPipeline,
        sim_time: float,
    ) -> None:
        target = fault.target
        ftype = fault.type
        params = fault.parameters

        if target.startswith("sensor."):
            self._apply_sensor_fault(target, ftype, params, sensors)
        elif target.startswith("transport."):
            self._apply_transport_fault(target, ftype, params, transport)
        elif target == "hardware.compute":
            self._apply_compute_fault(ftype, params, hardware, sim_time, fault.id)
        elif target.startswith("actuator."):
            self._apply_actuator_fault(target, ftype, params, actuators)

    def _revert_sensor_fault(self, target: str, ftype: str, sensors: dict[str, BaseSensor]) -> None:
        sensor_key = target.replace("sensor.", "")
        sensor = sensors.get(sensor_key)
        if not sensor:
            return
        if ftype == "dropout":
            sensor.dropout_active = False
        elif ftype == "freeze":
            sensor.is_frozen = False
            sensor._frozen_packet = None
        elif ftype == "noise_burst":
            sensor.noise_scale = 1.0
        elif ftype == "bias_offset":
            sensor.bias_offset = 0.0
        elif ftype == "sector_loss" and isinstance(sensor, LidarSensor):
            sensor.dropped_sectors.clear()
        elif ftype == "phantom_returns" and isinstance(sensor, LidarSensor):
            sensor.phantom_return_rate = 0.0
        elif ftype == "occlusion" and isinstance(sensor, CameraSensor):
            sensor.is_occluded = False
        elif ftype == "frame_drop" and isinstance(sensor, CameraSensor):
            sensor.frame_drop_rate = 0.0
        elif ftype == "confidence_degradation" and isinstance(sensor, CameraSensor):
            sensor.confidence_degradation = 0.0
        elif ftype == "position_jump" and isinstance(sensor, PositionSensor):
            sensor.trigger_jump(0.0, 0.0)

    def _revert_transport_fault(self, target: str, ftype: str, params: dict[str, Any], transport: TransportBus) -> None:
        channel_name = target.replace("transport.", "sensor.")
        channel = transport.get_channel(channel_name)
        if ftype == "added_latency":
            added_s = params.get("latency_ms", 300.0) / 1000.0
            channel.base_latency_s = max(channel.default_base_latency_s, channel.base_latency_s - added_s)
        elif ftype == "packet_loss":
            channel.packet_loss_rate = channel.default_packet_loss_rate
        elif ftype == "jitter":
            channel.jitter_std_s = channel.default_jitter_std_s

    def _revert_actuator_fault(self, target: str, ftype: str, params: dict[str, Any], actuators: ActuatorPipeline) -> None:
        actuator_type = target.replace("actuator.", "")
        if actuator_type == "brake":
            if ftype == "reduced_effectiveness":
                actuators.brake_effectiveness_factor = 1.0
            elif ftype == "extra_delay":
                delay_s = params.get("delay_ms", 200.0) / 1000.0
                actuators.extra_delay_s = max(0.0, actuators.extra_delay_s - delay_s)
            elif ftype == "dropped_command":
                actuators.dropped_command_prob = 0.0
        elif actuator_type == "steering":
            if ftype == "stuck_value":
                actuators.stuck_steering_angle = None
            elif ftype == "extra_delay":
                delay_s = params.get("delay_ms", 200.0) / 1000.0
                actuators.extra_delay_s = max(0.0, actuators.extra_delay_s - delay_s)
        elif actuator_type == "throttle":
            if ftype == "reduced_effectiveness":
                actuators.throttle_effectiveness_factor = 1.0

    def _revert_fault(
        self,
        fault: FaultDefinition,
        sensors: dict[str, BaseSensor],
        transport: TransportBus,
        hardware: VirtualEdgeScheduler,
        actuators: ActuatorPipeline,
    ) -> None:
        target = fault.target
        ftype = fault.type
        params = fault.parameters

        if target.startswith("sensor."):
            self._revert_sensor_fault(target, ftype, sensors)
        elif target.startswith("transport."):
            self._revert_transport_fault(target, ftype, params, transport)
        elif target == "hardware.compute":
            if ftype == "cpu_availability":
                hardware.profile.cpu_availability_ratio = 1.0
            elif ftype == "thermal_spike":
                hardware.profile.current_temperature = max(
                    hardware.profile.thermal_ambient_temp,
                    hardware.profile.current_temperature - float(params.get("temp_increase", 40.0)),
                )
            elif ftype == "overload":
                overload_id = f"fault_overload_{fault.id}"
                hardware.task_queue[:] = [
                    task for task in hardware.task_queue if task.task_id != overload_id
                ]
        elif target.startswith("actuator."):
            self._revert_actuator_fault(target, ftype, params, actuators)

    def reset(self) -> None:
        """Resets active fault tracking state."""
        self._active_fault_ids.clear()
