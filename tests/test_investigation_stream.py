"""Tests for immediate, non-blocking investigation event delivery."""

from __future__ import annotations

import asyncio
import queue
from types import SimpleNamespace

from backend.ws.live_stream import _next_investigation_event


def test_next_investigation_event_wakes_for_queued_event() -> None:
    """The stream waits on the queue and returns the event without timer polling."""
    event = object()
    subscription = SimpleNamespace(queue=queue.Queue())
    subscription.queue.put(event)

    received = asyncio.run(_next_investigation_event(subscription))

    assert received is event
