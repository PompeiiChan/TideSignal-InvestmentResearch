"""Tests for LangGraph runner incremental SSE pumping."""

from __future__ import annotations

import asyncio

import pytest

from backend.src.integrations.langgraph.runner import LangGraphRunner
from backend.src.integrations.langgraph.status_phases import ProgressTimelineTracker


@pytest.mark.asyncio
async def test_yield_events_during_task_emits_incremental_queue_events() -> None:
    """Stream queue events should be yielded before the graph task completes."""
    queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()

    async def graph() -> dict[str, object]:
        for chunk in ("泸", "州", "老窖"):
            await asyncio.sleep(0.03)
            queue.put_nowait({"event": "content_delta", "data": {"delta": chunk}})
        return {"final_response": "泸州老窖"}

    task = asyncio.create_task(graph())
    events: list[dict[str, object]] = []
    async for event in LangGraphRunner._yield_events_during_task(queue, task, poll_interval_s=0.01):
        events.append(event)

    assert [item["data"]["delta"] for item in events] == ["泸", "州", "老窖"]  # type: ignore[index]


def test_non_streaming_path_drains_response_stream_start_before_content_done() -> None:
    """Queued response_stream_start must be drained before content_done is yielded."""
    queue: asyncio.Queue[dict[str, object]] = asyncio.Queue()
    events: list[dict[str, object]] = []

    def stream_callback(event: dict[str, object]) -> None:
        queue.put_nowait(event)

    tracker = ProgressTimelineTracker(stream_callback)
    tracker.on_response_stream_start()

    for event in LangGraphRunner._drain_stream_queue(queue):
        events.append(event)
    events.append({"event": "content_done", "data": {"content": "澄清追问"}})

    event_names = [str(event["event"]) for event in events]
    assert "response_stream_start" in event_names
    assert "content_done" in event_names
    assert event_names.index("response_stream_start") < event_names.index("content_done")
