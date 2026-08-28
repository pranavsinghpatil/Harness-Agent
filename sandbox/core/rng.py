"""Seeded Pseudo-Random Number Generator Manager with subsystem stream isolation."""

from __future__ import annotations
import random
import numpy as np


class RngManager:
    """Manages independent, deterministic random number generator streams per subsystem."""

    def __init__(self, master_seed: int = 42) -> None:
        self._master_seed = master_seed
        self._subsystem_rngs: dict[str, np.random.Generator] = {}
        self._reseed(master_seed)

    @property
    def master_seed(self) -> int:
        return self._master_seed

    def _reseed(self, seed: int) -> None:
        """Derive reproducible child seeds for each subsystem."""
        self._master_seed = seed
        master_gen = np.random.SeedSequence(seed)
        subsystems = [
            "core",
            "world",
            "physics",
            "sensors",
            "transport",
            "hardware",
            "actuators",
            "faults",
            "agent",
        ]
        child_sequences = master_gen.spawn(len(subsystems))
        self._subsystem_rngs = {
            subsys: np.random.default_rng(seq)
            for subsys, seq in zip(subsystems, child_sequences)
        }

    def get(self, subsystem: str) -> np.random.Generator:
        """Retrieve the isolated numpy Generator for a subsystem."""
        if subsystem not in self._subsystem_rngs:
            # Dynamically derive a stable seed for new subsystems
            seed_hash = hash((self._master_seed, subsystem)) & 0xFFFFFFFF
            self._subsystem_rngs[subsystem] = np.random.default_rng(seed_hash)
        return self._subsystem_rngs[subsystem]

    def reset(self, master_seed: int | None = None) -> None:
        """Reset all RNG streams to initial or new master seed."""
        new_seed = self._master_seed if master_seed is None else master_seed
        self._reseed(new_seed)
