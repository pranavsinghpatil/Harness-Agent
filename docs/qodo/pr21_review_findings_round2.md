# PR #21 Qodo Review Findings - Round 2

- **PR:** https://github.com/pranavsinghpatil/Harness-Agent/pull/21
- **Branch:** `fix/investigation-stream-async`
- **Findings:** 3 total; all resolved.
- **Verification:** `uv run --no-sync pytest tests/test_investigation_stream.py tests/test_backend_investigation_e2e.py -q` -> 2 passed, 1 existing warning.

## Resolutions

1. **`event_queue` lacks type annotation**: removed the blocking queue bridge
   and typed the event-loop queue explicitly.
2. **Test locals lack annotations**: added explicit annotations to the stream
   test subscription, event, and received value.
3. **Idle streams exhaust executor**: added `subscribe_async()` with a
   thread-safe `loop.call_soon_threadsafe()` handoff into `asyncio.Queue`, so
   idle sockets consume no executor worker; replay/live event IDs are
   deduplicated across the subscription race.
