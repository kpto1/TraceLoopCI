"""pytest plugin: automatically records LLM calls during test runs."""

import time
import json
import pytest
import httpx


def pytest_addoption(parser):
    group = parser.getgroup("traceloop")
    group.addoption(
        "--traceloop-url",
        default="http://localhost:8000",
        help="TraceLoop CI API URL",
    )
    group.addoption(
        "--traceloop-key",
        default="",
        help="TraceLoop CI API key",
    )
    group.addoption(
        "--traceloop-project",
        default="default",
        help="Project ID for trace grouping",
    )


class TraceRecorder:
    def __init__(self, config):
        self.url = config.getoption("--traceloop-url", "http://localhost:8000")
        self.key = config.getoption("--traceloop-key", "")
        self.project = config.getoption("--traceloop-project", "default")
        self._client = None

    async def _get_client(self):
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def record(self, input_text, model_output, model="unknown", **kwargs):
        client = await self._get_client()
        payload = {
            "user_input": input_text,
            "model_output": model_output,
            "model": model,
            "project_id": self.project,
            **kwargs,
        }
        try:
            resp = await client.post(
                f"{self.url}/v1/traces",
                json=payload,
                headers={"X-API-Key": self.key} if self.key else {},
            )
            if resp.status_code != 200:
                print(f"[traceloop] Record failed: {resp.status_code}")
        except Exception as e:
            print(f"[traceloop] Record error: {e}")


_recorder = None


@pytest.hookimpl(trylast=True)
def pytest_configure(config):
    global _recorder
    if config.getoption("--traceloop-url"):
        _recorder = TraceRecorder(config)


def pytest_unconfigure(config):
    global _recorder
    _recorder = None


@pytest.fixture
def trace_loop(request):
    """Fixture that records LLM calls during a test."""
    if _recorder is None:
        pytest.skip("TraceLoop not configured (use --traceloop-url)")

    calls = []

    class Recorder:
        @staticmethod
        async def record(input_text, model_output, model="unknown", **kwargs):
            calls.append({"input": input_text, "output": model_output, "model": model})
            await _recorder.record(input_text, model_output, model, **kwargs)

    yield Recorder()
