"""Adapter mapping declarative HardwarePreset properties into SandboxEnvironment execution dynamics."""

from __future__ import annotations
from typing import TYPE_CHECKING
import copy

if TYPE_CHECKING:
    from sandbox.api.environment import SandboxEnvironment
    from harness.hardware.presets import HardwarePreset


class HardwareAdapter:
    """Configures sandbox hardware scheduling, transport latencies, and thermal limits from a HardwarePreset."""

    @staticmethod
    def apply_preset(env: SandboxEnvironment, preset: HardwarePreset) -> None:
        """Apply hardware preset parameters to the active sandbox environment.

        Args:
            env: Target SandboxEnvironment instance.
            preset: HardwarePreset defining board compute capacity and bus latencies.
        """
        # 1. Update Virtual Edge Scheduler CPU and Thermal model
        profile_copy = copy.deepcopy(preset.profile)
        if hasattr(env, "hardware"):
            env.hardware.profile = profile_copy
        elif hasattr(env, "hardware_scheduler"):
            env.hardware_scheduler.profile = profile_copy

        # 2. Configure baseline transport channel latencies
        if "camera" in env.transport.channels and "camera_mipi" in preset.transport_latencies:
            mipi = preset.transport_latencies["camera_mipi"]
            env.transport.channels["camera"].base_latency_s = mipi.get("base_latency_s", 0.015)
            env.transport.channels["camera"].jitter_std_s = mipi.get("jitter_std_s", 0.002)

        if "lidar" in env.transport.channels and "lidar_serial" in preset.transport_latencies:
            serial = preset.transport_latencies["lidar_serial"]
            env.transport.channels["lidar"].base_latency_s = serial.get("base_latency_s", 0.005)
            env.transport.channels["lidar"].jitter_std_s = serial.get("jitter_std_s", 0.001)

        if "imu" in env.transport.channels and "imu_i2c" in preset.transport_latencies:
            i2c = preset.transport_latencies["imu_i2c"]
            env.transport.channels["imu"].base_latency_s = i2c.get("base_latency_s", 0.0008)
            env.transport.channels["imu"].jitter_std_s = i2c.get("jitter_std_s", 0.0001)
