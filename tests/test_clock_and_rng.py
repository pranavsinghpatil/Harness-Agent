"""Tests for discrete SimClock, EventQueue, and isolated RngManager."""

import pytest
from sandbox.core.clock import SimClock, EventQueue
from sandbox.core.rng import RngManager


def test_clock_progression() -> None:
    clock = SimClock(start_time=0.0)
    assert clock.current_time == 0.0
    assert clock.step_count == 0

    clock.advance_by(0.01)
    assert clock.current_time == 0.01
    assert clock.step_count == 1

    clock.advance_to(1.5)
    assert clock.current_time == 1.5


def test_clock_rejects_invalid_dt() -> None:
    clock = SimClock(start_time=1.0)
    with pytest.raises(ValueError):
        clock.advance_by(0.0)

    with pytest.raises(ValueError):
        clock.advance_by(-0.1)

    with pytest.raises(ValueError):
        clock.advance_to(0.5)  # Cannot rewind


def test_event_queue_deterministic_order() -> None:
    q = EventQueue()
    # Add events out of order
    q.push(timestamp=1.5, event_type="sensor", payload="A", priority=1)
    q.push(timestamp=0.5, event_type="actuator", payload="B", priority=1)
    q.push(timestamp=0.5, event_type="safety", payload="C", priority=0)  # higher priority

    e1 = q.pop()
    assert e1 is not None
    assert e1.timestamp == 0.5
    assert e1.event_type == "safety"

    e2 = q.pop()
    assert e2 is not None
    assert e2.timestamp == 0.5
    assert e2.event_type == "actuator"

    e3 = q.pop()
    assert e3 is not None
    assert e3.timestamp == 1.5
    assert e3.event_type == "sensor"

    assert q.is_empty


def test_rng_manager_isolation() -> None:
    # Same master seed must produce identical numbers
    rng1 = RngManager(master_seed=1234)
    rng2 = RngManager(master_seed=1234)

    val1 = rng1.get("sensors").normal(0.0, 1.0)
    val2 = rng2.get("sensors").normal(0.0, 1.0)
    assert val1 == val2

    # Drawing from 'sensors' does NOT alter 'physics' sequence
    rng_a = RngManager(master_seed=999)
    rng_b = RngManager(master_seed=999)

    # Draw 100 values from sensors in A
    for _ in range(100):
        rng_a.get("sensors").uniform()

    # Physics in A and B must still be perfectly identical
    phys_a = rng_a.get("physics").uniform(0, 10, size=5)
    phys_b = rng_b.get("physics").uniform(0, 10, size=5)
    assert list(phys_a) == list(phys_b)
