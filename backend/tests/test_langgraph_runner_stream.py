"""Tests for LangGraph runner incremental SSE pumping."""

from __future__ import annotations

import asyncio

import pytest

from backend.src.integrations.langgraph.runner import LangGraphRunner


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
