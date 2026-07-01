"""
pytest configuration for TraceLoop CI plugin demo.

This file is auto-discovered by pytest. It configures the trace_loop
plugin so that every test that uses the `trace_loop` fixture will
automatically record LLM call traces to the configured server.

Usage:
    pytest --traceloop-url http://localhost:8000 --traceloop-api-key tl_dev_key
"""

import pytest


def pytest_addoption(parser):
    """Register custom CLI flags for the TraceLoop plugin."""
    parser.addoption(
        "--traceloop-url",
        action="store",
        default="http://localhost:8000",
        help="TraceLoop CI server URL (default: http://localhost:8000)",
    )
    parser.addoption(
        "--traceloop-api-key",
        action="store",
        default=None,
        help="API key for the TraceLoop server (default: none)",
    )
    parser.addoption(
        "--traceloop-session",
        action="store",
        default=None,
        help="Optional session ID to group related test runs together",
    )


@pytest.fixture
def traceloop_config(request):
    """
    Fixture that provides the TraceLoop connection config to tests.

    Other fixtures (like `trace_loop`) can depend on this to avoid
    parsing CLI flags themselves.
    """
    return {
        "url": request.config.getoption("--traceloop-url"),
        "api_key": request.config.getoption("--traceloop-api-key"),
        "session": request.config.getoption("--traceloop-session"),
    }


@pytest.fixture
def trace_loop(traceloop_config):
    """
    Fixture that provides a configured TraceLoop client to test functions.

    Tests that use this fixture will automatically:
      1. Create a recording context around each test
      2. Intercept any LLM API calls made during the test
      3. Upload traces to the TraceLoop server on test completion
      4. Tag traces with the test name and outcome (pass/fail)

    In a real implementation this wraps the TraceLoop SDK client.
    For this demo we return a lightweight dict with the same shape.
    """
    from uuid import uuid4

    # In production: return TraceLoopClient(url=..., api_key=...)
    client = {
        "url": traceloop_config["url"],
        "api_key": traceloop_config["api_key"],
        "session_id": traceloop_config["session"] or str(uuid4())[:8],
        "_traces": [],  # collected during the test
    }

    yield client

    # Teardown: flush any traces that weren't sent
    if client["_traces"]:
        import httpx

        headers = {"Content-Type": "application/json"}
        if client["api_key"]:
            headers["Authorization"] = f"Bearer {client['api_key']}"

        for payload in client["_traces"]:
            try:
                httpx.post(
                    f"{client['url']}/v1/traces",
                    json=payload,
                    headers=headers,
                    timeout=5,
                )
            except Exception:
                pass  # Don't fail the test if flush fails
