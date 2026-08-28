"""Discrete simulation clock and priority event queue for deterministic execution."""

from __future__ import annotations
import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


@dataclass(order=True)
class SimEvent:
    """An event scheduled in simulation time."""
    timestamp: float
    priority: int = 0  # Lower number = higher priority
    event_id: int = field(default=0, compare=True)
    event_type: str = field(default="", compare=False)
    payload: Any = field(default=None, compare=False)
    callback: Optional[Callable[..., Any]] = field(default=None, compare=False)


class EventQueue:
    """Deterministic priority event queue backed by a min-heap."""

    def __init__(self) -> None:
        self._heap: list[SimEvent] = []
        self._counter: int = 0

    def push(
        self,
        timestamp: float,
        event_type: str,
        payload: Any = None,
        callback: Optional[Callable[..., Any]] = None,
        priority: int = 0,
    ) -> SimEvent:
        """Schedule a new event."""
        self._counter += 1
        event = SimEvent(
            timestamp=round(timestamp, 9),  # 1 ns precision to avoid float noise
            priority=priority,
            event_id=self._counter,
            event_type=event_type,
            payload=payload,
            callback=callback,
        )
        heapq.heappush(self._heap, event)
        return event

    def pop(self) -> Optional[SimEvent]:
        """Pop the next earliest event."""
        if self._heap:
            return heapq.heappop(self._heap)
        return None

    def peek(self) -> Optional[SimEvent]:
        """Inspect the next earliest event without removing it."""
        if self._heap:
            return self._heap[0]
        return None

    def clear(self) -> None:
        """Clear all events."""
        self._heap.clear()
        self._counter = 0

    def __len__(self) -> int:
        return len(self._heap)

    @property
    def is_empty(self) -> bool:
        return len(self._heap) == 0


class SimClock:
    """Discrete simulation clock managing virtual time progression."""

    def __init__(self, start_time: float = 0.0) -> None:
        self._current_time: float = round(start_time, 9)
        self._start_time: float = self._current_time
        self._step_count: int = 0
        self._is_paused: bool = False

    @property
    def current_time(self) -> float:
        """Get current simulation time in seconds."""
        return self._current_time

    @property
    def step_count(self) -> int:
        """Get total simulation steps taken."""
        return self._step_count

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    def pause(self) -> None:
        self._is_paused = True

    def resume(self) -> None:
        self._is_paused = False

    def advance_by(self, dt: float) -> float:
        """Advance time by a fixed delta (dt > 0)."""
        if dt <= 0:
            raise ValueError(f"Time delta dt must be strictly positive, got {dt}")
        self._current_time = round(self._current_time + dt, 9)
        self._step_count += 1
        return self._current_time

    def advance_to(self, target_time: float) -> float:
        """Advance time to a specific target time (target_time >= current_time)."""
        target_time = round(target_time, 9)
        if target_time < self._current_time:
            raise ValueError(
                f"Cannot rewind time from {self._current_time} to {target_time}"
            )
        self._current_time = target_time
        self._step_count += 1
        return self._current_time

    def reset(self, start_time: float = 0.0) -> None:
        """Reset the clock."""
        self._current_time = round(start_time, 9)
        self._start_time = self._current_time
        self._step_count = 0
        self._is_paused = False
