"""Tests for immediate, non-blocking investigation event delivery."""

from __future__ import annotations

import asyncio

from harness.models.events import HarnessEvent, HarnessEventType
from harness.investigator import InvestigatorConfig
from harness.orchestration.investigation import (
    InvestigationEventSubscription,
    InvestigationSession,
)


def test_async_subscription_wakes_for_queued_event() -> None:
    """The session hands worker-thread events to an event-loop-native queue."""
    session: InvestigationSession = InvestigationSession(
        InvestigatorConfig(objective="stream test", budget=1)
    )

    async def receive() -> HarnessEvent:
        """Receive the event through the async subscriber queue."""
        subscription: InvestigationEventSubscription = session.subscribe_async()
        expected: HarnessEvent = HarnessEvent(
            evaluation_id="eval", run_id="run", episode_id="episode", sim_time=0.0,
            source="test", type=HarnessEventType.INVESTIGATION_STARTED,
        )
        session._fan_out(expected)
        assert subscription.async_queue is not None
        received: HarnessEvent = await subscription.async_queue.get()
        return received

    received: HarnessEvent = asyncio.run(receive())
    assert received.type == HarnessEventType.INVESTIGATION_STARTED
