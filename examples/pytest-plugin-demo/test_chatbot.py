"""Explicit recording through the real pytest plugin, no automatic interception."""

import pytest


@pytest.mark.asyncio
async def test_chatbot(trace_loop):
    question = "Refund policy?"
    answer = "Refunds are available within 7 days."
    await trace_loop.record(question, answer, model="demo")
    assert "7 days" in answer
