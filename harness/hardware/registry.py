"""Hardware preset registry and discovery service."""

from __future__ import annotations
from typing import Dict, List, Optional
from harness.hardware.presets import (
    HardwarePreset,
    RDK_X5_PRESET,
    JETSON_ORIN_NANO_PRESET,
    RASPBERRY_PI_5_PRESET,
)


class HardwareRegistry:
    """Registry maintaining available edge board hardware profiles."""

    def __init__(self) -> None:
        self._presets: Dict[str, HardwarePreset] = {}
        self.register(RDK_X5_PRESET)
        self.register(JETSON_ORIN_NANO_PRESET)
        self.register(RASPBERRY_PI_5_PRESET)

    def register(self, preset: HardwarePreset) -> None:
        """Register a new hardware preset.

        Args:
            preset: Hardware preset instance to register.
        """
        self._presets[preset.id.upper()] = preset

    def get(self, preset_id: str) -> HardwarePreset:
        """Lookup a hardware preset by ID, falling back to D-Robotics RDK X5.

        Args:
            preset_id: Hardware identifier (case-insensitive).

        Returns:
            The matched HardwarePreset or default RDK_X5_PRESET.
        """
        clean_id = preset_id.upper()
        return self._presets.get(clean_id, RDK_X5_PRESET)

    def list_presets(self) -> List[HardwarePreset]:
        """List all available hardware presets.

        Returns:
            List of registered HardwarePreset objects.
        """
        return list(self._presets.values())


# Global registry singleton
default_hardware_registry = HardwareRegistry()
