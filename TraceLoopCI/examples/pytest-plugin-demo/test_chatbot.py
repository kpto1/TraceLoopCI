"""
Tests for a hypothetical chatbot, instrumented with TraceLoop CI.

Each test uses the `trace_loop` fixture (from conftest.py) to record
LLM interactions. When run with `pytest --traceloop-url http://...`,
the traces are uploaded to the TraceLoop server automatically.

These tests use mocked responses — no real LLM API key is required.
"""

import datetime
import uuid
import time


# -------------------------------------------------------------------
# A fake LLM client for demo purposes
# -------------------------------------------------------------------
class FakeLLMClient:
    """
    Stand-in for an LLM provider SDK (e.g. openai.ChatCompletion).

    In production, the TraceLoop SDK would intercept the real HTTP calls
    automatically. Here we manually push trace data to the fixture.
    """

    def __init__(self, trace_loop_fixture):
        self._fixture = trace_loop_fixture

    def chat(self, messages: list[dict], model: str = "gpt-4o-mini") -> str:
        """Simulate sending messages to an LLM and recording the trace."""

        # Build a fake response
        response_text = (
            f"I received {len(messages)} message(s). "
            "This is a simulated LLM response for testing."
        )

        # Build the trace payload
        trace = {
            "session_id": self._fixture["session_id"],
            "timestamp": time.time(),
            "model": model,
            "provider": "openai",
            "request": {
                "messages": messages,
                "temperature": 0.7,
            },
            "response": {
                "role": "assistant",
                "content": response_text,
                "finish_reason": "stop",
            },
            "usage": {
                "prompt_tokens": sum(len(m.get("content", "")) for m in messages) // 4,
                "completion_tokens": len(response_text) // 4,
                "total_tokens": 0,  # computed below
            },
        }
        trace["usage"]["total_tokens"] = (
            trace["usage"]["prompt_tokens"] + trace["usage"]["completion_tokens"]
        )

        # Store in the fixture so it gets flushed after the test
        self._fixture["_traces"].append(trace)

        return response_text


# -------------------------------------------------------------------
# Helper to create test users
# -------------------------------------------------------------------
def make_user(role: str) -> dict:
    return {"user_id": str(uuid.uuid4())[:8], "role": role, "created_at": datetime.datetime.now().isoformat()}


# -------------------------------------------------------------------
# Tests
# -------------------------------------------------------------------
class TestChatbot:
    """
    A test suite demonstrating TraceLoop CI integration.

    Run with:  pytest --traceloop-url http://localhost:8000 -v
    """

    def test_greeting_response(self, trace_loop):
        """Verify the chatbot responds to a basic greeting."""
        client = FakeLLMClient(trace_loop)
        messages = [{"role": "user", "content": "Hello, how are you?"}]

        response = client.chat(messages)

        assert response is not None
        assert len(response) > 0
        # Traces were automatically recorded in trace_loop["_traces"]

    def test_follow_up_question(self, trace_loop):
        """Verify multi-turn conversation handling."""
        client = FakeLLMClient(trace_loop)
        messages = [
            {"role": "user", "content": "What is Python?"},
            {"role": "assistant", "content": "Python is a programming language."},
            {"role": "user", "content": "Is it good for data science?"},
        ]

        response = client.chat(messages)

        assert response is not None
        # The trace records all 3 messages in the conversation history

    def test_long_context_preserved(self, trace_loop):
        """Verify long prompts don't break the tracer."""
        long_text = "word " * 2000  # ~10k chars
        client = FakeLLMClient(trace_loop)

        response = client.chat([{"role": "user", "content": long_text}])

        assert response is not None
        # Verify the trace was captured despite the large payload
        assert len(trace_loop["_traces"]) == 1
        trace = trace_loop["_traces"][0]
        assert trace["usage"]["prompt_tokens"] > 0

    def test_trace_metadata(self, trace_loop):
        """Verify traces contain correct metadata."""
        client = FakeLLMClient(trace_loop)

        client.chat(
            [{"role": "user", "content": "Tell me a joke"}],
            model="gpt-4",
        )

        trace = trace_loop["_traces"][0]
        assert trace["model"] == "gpt-4"
        assert trace["provider"] == "openai"
        assert trace["session_id"] == trace_loop["session_id"]
        assert "request" in trace
        assert "response" in trace
        assert "usage" in trace

    def test_no_empty_traces(self, trace_loop):
        """Verify no trace is sent when no LLM call is made."""
        # Intentionally NOT calling client.chat() — should produce 0 traces
        assert len(trace_loop["_traces"]) == 0

    def test_system_prompt_recorded(self, trace_loop):
        """Verify system prompts are included in trace data."""
        client = FakeLLMClient(trace_loop)
        messages = [
            {"role": "system", "content": "You are a pirate. Always speak like one."},
            {"role": "user", "content": "Where is the treasure?"},
        ]

        client.chat(messages)

        trace = trace_loop["_traces"][0]
        system_msg = trace["request"]["messages"][0]
        assert system_msg["role"] == "system"
        assert "pirate" in system_msg["content"]
