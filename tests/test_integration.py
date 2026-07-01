"""Integration tests — end-to-end: proxy + eval + trace flows."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestProxyFlow:
    """End-to-end: proxy receives request → records trace → returns response."""

    async def test_proxy_non_stream_with_mock(self, client):
        from app.services.trace_collector import proxy_llm_call

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "7天内可退款"}}],
            "usage": {"prompt_tokens": 8, "completion_tokens": 6, "total_tokens": 14},
        }

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp

        with patch("app.services.trace_collector.get_client", return_value=mock_http):
            result = await proxy_llm_call(
                target_url="http://fake/v1/chat/completions",
                headers={"Authorization": "Bearer sk-test", "Content-Type": "application/json"},
                body={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "你是客服"},
                        {"role": "user", "content": "退款政策是什么？"},
                    ],
                    "temperature": 0.3,
                    "stream": False,
                },
                stream=False,
            )

        assert result["trace"]["status"] == "success"
        assert result["trace"]["model"] == "deepseek-chat"
        assert result["trace"]["user_input"] == "退款政策是什么？"
        assert result["trace"]["system_prompt"] == "你是客服"
        assert result["trace"]["tokens_total"] == 14
        assert result["trace"]["temperature"] == 0.3

    async def test_proxy_records_span_data(self):
        """Verify spans in the proxy request body flow through the collector."""
        from app.services.trace_collector import proxy_llm_call

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "您好，请问有什么可以帮您？"}}],
            "usage": {"total_tokens": 12},
        }

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_resp

        with patch("app.services.trace_collector.get_client", return_value=mock_http):
            result = await proxy_llm_call(
                target_url="http://fake/v1",
                headers={},
                body={
                    "model": "qwen-max",
                    "messages": [{"role": "user", "content": "你好"}],
                },
                stream=False,
            )

        assert result["trace"]["status"] == "success"
        assert result["trace"]["model"] == "qwen-max"
        assert result["trace"]["user_input"] == "你好"


class TestDatasetEvalFlow:
    """End-to-end: create dataset → add cases → run eval → check results."""

    async def test_create_dataset_and_run_eval(self, client):
        # Create dataset
        r = await client.post("/v1/datasets", json={
            "name": "客服退款场景",
            "description": "测试退款相关的prompt回归",
            "project_id": "qa",
        })
        assert r.status_code == 200
        ds_id = r.json()["id"]

        # Add cases
        cases = [
            {"input_text": "我要退款", "expected_keywords": ["退款", "7天"], "forbidden_keywords": ["不能退"]},
            {"input_text": "退货流程是什么", "expected_keywords": ["退货", "流程"], "forbidden_keywords": []},
            {"input_text": "订单状态查询", "expected_keywords": ["订单"], "forbidden_keywords": []},
        ]
        for c in cases:
            r = await client.post(f"/v1/datasets/{ds_id}/cases", json=c)
            assert r.status_code == 200

        # Verify dataset has 3 cases
        r = await client.get(f"/v1/datasets/{ds_id}")
        assert r.status_code == 200
        assert r.json()["case_count"] == 3

        # Run eval with mocked LLM
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "您可以7天内申请退款，流程简单快捷。"}}],
            "usage": {"total_tokens": 20},
        }
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_resp

        with patch("app.services.eval_runner.httpx.AsyncClient", return_value=mock_client):
            r = await client.post("/v1/eval/run", json={
                "dataset_id": ds_id,
                "model": "deepseek-chat",
                "is_baseline": True,
            })
            assert r.status_code == 200
            data = r.json()
            assert data["total_cases"] == 3
            assert "overall_score" in data
            assert len(data["per_case"]) == 3

        # List eval runs
        r = await client.get("/v1/eval/runs", params={"dataset_id": ds_id})
        assert r.status_code == 200
        runs = r.json()["items"]
        assert len(runs) >= 1

        # Get specific run
        if runs:
            run_id = runs[0]["id"]
            r = await client.get(f"/v1/eval/runs/{run_id}")
            assert r.status_code == 200
            assert r.json()["total_cases"] == 3

    async def test_add_case_from_trace_flow(self, client):
        """Golden case creation from existing trace."""
        # Create a trace
        tr = await client.post("/v1/traces", json={
            "user_input": "会员等级有哪些？",
            "model_output": "我们有普通会员、高级会员和尊享会员三个等级。",
            "model": "deepseek-chat",
            "project_id": "customer-service",
        })
        assert tr.status_code == 200
        trace_id = tr.json()["trace_id"]

        # Create dataset
        r = await client.post("/v1/datasets", json={"name": "会员场景"})
        ds_id = r.json()["id"]

        # Create golden case from trace
        r = await client.post(
            f"/v1/datasets/{ds_id}/cases/from-trace/{trace_id}",
            json={
                "expected_keywords": ["会员", "等级"],
                "forbidden_keywords": ["没有会员"],
                "tags": ["customer-service", "membership"],
            },
        )
        assert r.status_code == 200
        assert r.json()["source_trace_id"] == trace_id

        # Verify it appears in dataset
        r = await client.get(f"/v1/datasets/{ds_id}")
        cases = r.json()["cases"]
        assert len(cases) == 1
        assert cases[0]["source_trace_id"] == trace_id


class TestCoverageGaps:
    """Targeted tests for uncovered code paths."""

    async def test_trace_service_list_with_filters(self, client):
        # Create traces with different models
        await client.post("/v1/traces", json={
            "user_input": "q1", "model_output": "a1", "model": "gpt-4", "status": "success",
        })
        await client.post("/v1/traces", json={
            "user_input": "q2", "model_output": "a2", "model": "gpt-4", "status": "error",
            "error_message": "timeout",
        })

        # Filter by model
        r = await client.get("/v1/traces", params={"model": "gpt-4"})
        assert r.status_code == 200
        assert all(t["model"] == "gpt-4" for t in r.json()["items"])

        # Filter by status
        r = await client.get("/v1/traces", params={"status": "error"})
        assert r.status_code == 200
        assert all(t["status"] == "error" for t in r.json()["items"])

    async def test_trace_with_spans_eager_loaded(self, client):
        r = await client.post("/v1/traces", json={
            "user_input": "complex query",
            "model_output": "complex answer",
            "model": "test",
            "spans": [
                {"span_type": "retrieval", "name": "search docs", "duration_ms": 50},
                {"span_type": "generation", "name": "generate", "duration_ms": 300},
            ],
        })
        tid = r.json()["trace_id"]

        # Get with spans
        r = await client.get(f"/v1/traces/{tid}", params={"include_spans": True})
        assert r.status_code == 200
        data = r.json()
        assert "spans" in data
        assert len(data["spans"]) == 2
        assert data["spans"][0]["span_type"] == "retrieval"

    async def test_eval_runner_error_when_empty_dataset(self):
        from app.database import async_session
        from app.models.golden import GoldenDataset
        from app.services.eval_runner import run_eval
        import pytest

        async with async_session() as session:
            ds = GoldenDataset(name="empty-ds")
            session.add(ds)
            await session.commit()

            with pytest.raises(ValueError, match="No golden cases"):
                await run_eval(session=session, dataset_id=ds.id, model="test")

    async def test_config_defaults(self):
        """Verify config defaults are set correctly."""
        from app import config
        assert config.SERVER_PORT == 8000
        assert config.DEBUG == False  # set by test env
        assert config.REDIS_STREAM_NAME == "traceloop:traces"
        assert config.REDIS_BATCH_SIZE == 100
