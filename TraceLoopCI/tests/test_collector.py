import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestProxyLLMCall:
    async def test_non_stream_success(self):
        from app.services.trace_collector import proxy_llm_call

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Hello world"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        with patch("app.services.trace_collector.get_client", return_value=mock_client):
            result = await proxy_llm_call(
                target_url="http://fake/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test"},
                body={"model": "test", "messages": [{"role": "user", "content": "hi"}]},
                stream=False,
            )

        assert result["trace"]["status"] == "success"
        assert result["trace"]["model"] == "test"
        assert result["trace"]["model_output"] == "Hello world"
        assert result["trace"]["tokens_total"] == 15
        assert result["trace"]["latency_ms"] >= 0

    async def test_extracts_system_prompt(self):
        from app.services.trace_collector import proxy_llm_call

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"total_tokens": 7},
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        with patch("app.services.trace_collector.get_client", return_value=mock_client):
            result = await proxy_llm_call(
                target_url="http://fake/v1",
                headers={},
                body={
                    "model": "gpt-4",
                    "messages": [
                        {"role": "system", "content": "You are helpful"},
                        {"role": "user", "content": "What is 2+2?"},
                    ],
                },
                stream=False,
            )

        assert result["trace"]["system_prompt"] == "You are helpful"
        assert result["trace"]["user_input"] == "What is 2+2?"

    async def test_timeout_handled(self):
        from app.services.trace_collector import proxy_llm_call
        import httpx

        mock_client = AsyncMock()
        mock_client.post.side_effect = httpx.TimeoutException("too slow")

        with patch("app.services.trace_collector.get_client", return_value=mock_client):
            result = await proxy_llm_call(
                target_url="http://fake/v1",
                headers={},
                body={"model": "x", "messages": [{"role": "user", "content": "y"}]},
                stream=False,
            )

        assert result["trace"]["status"] == "error"
        assert "timeout" in result["trace"]["error_message"].lower()

    async def test_stream_success(self):
        from app.services.trace_collector import proxy_llm_call

        chunks = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n',
            'data: {"choices":[{"delta":{"content":" world"}}]}\n',
            'data: {"choices":[{"delta":{"content":"!"}}],"usage":{"total_tokens":8}}\n',
            'data: [DONE]\n',
        ]

        class FakeStreamResp:
            status_code = 200
            async def aiter_lines(self):
                for c in chunks:
                    yield c

        class FakeCtxMgr:
            async def __aenter__(self):
                return FakeStreamResp()
            async def __aexit__(self, *args):
                pass

        mock_client = MagicMock()
        mock_client.stream.return_value = FakeCtxMgr()
        mock_client.post = AsyncMock()

        with patch("app.services.trace_collector.get_client", return_value=mock_client):
            result = await proxy_llm_call(
                target_url="http://fake/v1",
                headers={},
                body={"model": "test", "messages": [{"role": "user", "content": "hi"}]},
                stream=True,
            )

        assert result["trace"]["status"] == "success"
        assert result["trace"]["model_output"] == "Hello world!"

    async def test_upstream_error(self):
        from app.services.trace_collector import proxy_llm_call

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.json.return_value = {"error": "internal error"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp

        with patch("app.services.trace_collector.get_client", return_value=mock_client):
            result = await proxy_llm_call(
                target_url="http://fake/v1",
                headers={},
                body={"model": "x", "messages": [{"role": "user", "content": "y"}]},
                stream=False,
            )

        assert result["trace"]["status"] == "error"


class TestProxyEndpoint:
    async def test_proxy_health(self, client):
        r = await client.get("/proxy/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
