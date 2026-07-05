import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestKeywordEval:
    async def test_all_keywords_found(self):
        from app.services.evaluators.keyword_eval import evaluate

        result = await evaluate(
            {"expected_keywords": ["退款", "7天"], "forbidden_keywords": []},
            "我们支持7天内退款，请提供订单号。",
        )
        assert result["passed"] is True
        assert result["score"] == 1.0
        assert "退款" in result["details"]["found_keywords"]
        assert "7天" in result["details"]["found_keywords"]

    async def test_missing_keyword_fails(self):
        from app.services.evaluators.keyword_eval import evaluate

        result = await evaluate(
            {"expected_keywords": ["退款", "30天"], "forbidden_keywords": []},
            "我们支持7天内退款。",
        )
        assert result["passed"] is False
        assert "30天" in result["details"]["missing_keywords"]

    async def test_forbidden_word_fails(self):
        from app.services.evaluators.keyword_eval import evaluate

        result = await evaluate(
            {"expected_keywords": [], "forbidden_keywords": ["不能退款"]},
            "抱歉，我们不能退款。",
        )
        assert result["passed"] is False
        assert "不能退款" in result["details"]["found_forbidden"]

    async def test_empty_rules_passes(self):
        from app.services.evaluators.keyword_eval import evaluate

        result = await evaluate(
            {"expected_keywords": [], "forbidden_keywords": []},
            "任意回答。",
        )
        assert result["passed"] is True


class TestJsonEval:
    async def test_valid_json_no_schema(self):
        from app.services.evaluators.json_eval import evaluate

        result = await evaluate(
            {"expected_json_schema": None},
            '{"answer": 42, "confidence": 0.95}',
        )
        assert result["passed"] is True

    async def test_valid_json_with_schema(self):
        from app.services.evaluators.json_eval import evaluate

        schema = {
            "type": "object",
            "properties": {"answer": {"type": "integer"}, "confidence": {"type": "number"}},
            "required": ["answer"],
        }
        result = await evaluate(
            {"expected_json_schema": schema},
            '{"answer": 42, "confidence": 0.95}',
        )
        assert result["passed"] is True

    async def test_schema_mismatch_fails(self):
        from app.services.evaluators.json_eval import evaluate

        result = await evaluate(
            {"expected_json_schema": {"type": "object", "required": ["name"]}},
            '{"answer": 42}',
        )
        assert result["passed"] is False

    async def test_invalid_json_fails_when_schema_required(self):
        from app.services.evaluators.json_eval import evaluate

        # When a schema is specified, invalid JSON still fails
        result = await evaluate(
            {"expected_json_schema": {"type": "object"}},
            'not valid json {{{',
        )
        assert result["passed"] is False

    async def test_no_schema_skips_json_validation(self):
        from app.services.evaluators.json_eval import evaluate

        # When no schema is specified, non-JSON output should NOT fail
        result = await evaluate(
            {"expected_json_schema": None},
            'this is plain text, not json',
        )
        assert result["passed"] is True
        assert result["details"].get("skipped") is True


class TestLLMJudge:
    async def test_mock_judge_passes_good_answer(self):
        from app.services.evaluators.llm_judge import evaluate

        result = await evaluate(
            {"input_text": "退款政策？", "expected_keywords": ["7天", "退款"], "forbidden_keywords": []},
            "我们支持7天内无理由退款。",
        )
        assert result["passed"] is True

    async def test_mock_judge_fails_forbidden(self):
        from app.services.evaluators.llm_judge import evaluate

        result = await evaluate(
            {"input_text": "退款？", "expected_keywords": ["退款"], "forbidden_keywords": ["不能退款"]},
            "抱歉，我们不能退款。",
        )
        assert result["passed"] is False

    async def test_parse_json_output(self):
        from app.services.evaluators.llm_judge import _parse_judge_output

        r = _parse_judge_output('{"score": 8, "reason": "准确"}')
        assert r["score"] == 8

    async def test_parse_markdown_output(self):
        from app.services.evaluators.llm_judge import _parse_judge_output

        r = _parse_judge_output('```json\n{"score": 6, "reason": "ok"}\n```')
        assert r["score"] == 6

    async def test_parse_fallback_chinese(self):
        from app.services.evaluators.llm_judge import _parse_judge_output

        r = _parse_judge_output("我认为可以给7分，回答基本正确")
        assert r["score"] == 7


class TestDatasetAPI:
    async def test_create_and_list(self, client):
        r = await client.post("/v1/datasets", json={"name": "客服场景"})
        assert r.status_code == 200
        ds_id = r.json()["id"]

        r2 = await client.get("/v1/datasets")
        assert r2.status_code == 200
        names = [d["name"] for d in r2.json()["items"]]
        assert "客服场景" in names

    async def test_add_case(self, client):
        r = await client.post("/v1/datasets", json={"name": "test-ds"})
        ds_id = r.json()["id"]

        r2 = await client.post(f"/v1/datasets/{ds_id}/cases", json={
            "input_text": "退款政策？",
            "expected_keywords": ["退款", "7天"],
            "forbidden_keywords": ["不能退款"],
        })
        assert r2.status_code == 200

    async def test_add_case_from_trace(self, client):
        # Create trace first
        tr = await client.post("/v1/traces", json={
            "user_input": "退款政策？", "model_output": "7天内退款", "model": "test",
        })
        trace_id = tr.json()["trace_id"]

        # Create dataset
        r = await client.post("/v1/datasets", json={"name": "from-trace"})
        ds_id = r.json()["id"]

        r2 = await client.post(f"/v1/datasets/{ds_id}/cases/from-trace/{trace_id}", json={
            "expected_keywords": ["退款"],
        })
        assert r2.status_code == 200

    async def test_trigger_eval(self, client):
        # Create dataset
        r = await client.post("/v1/datasets", json={"name": "eval-ds"})
        ds_id = r.json()["id"]

        await client.post(f"/v1/datasets/{ds_id}/cases", json={
            "input_text": "退款政策？",
            "expected_keywords": ["退款"],
            "forbidden_keywords": [],
        })

        # Mock the LLM call so it doesn't need external server
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "7天内可以退款"}}],
            "usage": {"total_tokens": 15},
        }

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_resp

        with patch("app.services.eval_runner.httpx.AsyncClient", return_value=mock_client):
            r3 = await client.post("/v1/eval/run", json={
                "dataset_id": ds_id, "model": "mock", "is_baseline": True,
            })
            assert r3.status_code == 200
            data = r3.json()
            assert data["total_cases"] == 1
            assert "per_case" in data
