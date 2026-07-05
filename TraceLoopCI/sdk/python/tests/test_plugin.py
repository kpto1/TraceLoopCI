import pytest


class TestTraceRecorder:
    def test_recorder_creation(self):
        from trace_loop.plugin import TraceRecorder

        class FakeConfig:
            def getoption(self, name, default=None):
                opts = {
                    "--traceloop-url": "http://localhost:8000",
                    "--traceloop-key": "test-key",
                    "--traceloop-project": "test-project",
                }
                return opts.get(name, default)

        recorder = TraceRecorder(FakeConfig())
        assert recorder.url == "http://localhost:8000"
        assert recorder.key == "test-key"
        assert recorder.project == "test-project"
