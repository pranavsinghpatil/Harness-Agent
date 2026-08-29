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

        # 2. Configure baseline transport channel latencies for all registered sensor channels
        channel_mappings = {
            "camera_mipi": ["sensor.camera", "camera"],
            "lidar_serial": ["sensor.lidar", "lidar"],
            "imu_i2c": ["sensor.imu", "imu"],
            "encoder_spi": ["sensor.encoder", "encoder"],
            "position_bus": ["sensor.position", "position"],
        }

        for preset_key, candidate_names in channel_mappings.items():
            if preset_key in preset.transport_latencies:
                cfg = preset.transport_latencies[preset_key]
                for ch_name in candidate_names:
                    if ch_name in env.transport.channels:
                        channel = env.transport.channels[ch_name]
                        channel.base_latency_s = cfg.get("base_latency_s", channel.base_latency_s)
                        channel.jitter_std_s = cfg.get("jitter_std_s", channel.jitter_std_s)
