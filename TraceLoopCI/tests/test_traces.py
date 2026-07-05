import pytest


class TestBasics:
    async def test_root(self, client):
        r = await client.get("/")
        assert r.status_code == 200
        assert r.json()["service"] == "TraceLoop CI"

    async def test_health(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestTraceWrite:
    async def test_minimal(self, client):
        r = await client.post("/v1/traces", json={
            "user_input": "退款政策是什么？",
            "model_output": "7天内可退款。",
            "model": "deepseek-chat",
        })
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert "trace_id" in r.json()

    async def test_full_payload(self, client):
        r = await client.post("/v1/traces", json={
            "user_input": "查订单",
            "model_output": "您的订单配送中",
            "model": "deepseek-chat",
            "provider": "deepseek",
            "system_prompt": "你是客服助手",
            "temperature": 0.7,
            "tokens_prompt": 15,
            "tokens_completion": 30,
            "tokens_total": 45,
            "cost": 0.0001,
            "latency_ms": 850,
            "ttft_ms": 200,
            "project_id": "customer-service",
            "tags": ["order"],
            "spans": [
                {"span_type": "retrieval", "name": "查知识库", "duration_ms": 120},
                {"span_type": "generation", "name": "生成回复", "duration_ms": 730},
            ],
        })
        assert r.status_code == 200

    async def test_missing_input_ok(self, client):
        r = await client.post("/v1/traces", json={"model_output": "x"})
        assert r.status_code == 200


class TestTraceRead:
    async def test_list(self, client):
        await client.post("/v1/traces", json={
            "user_input": "list test",
            "model_output": "ok",
            "model": "t1",
            "project_id": "p1",
        })
        r = await client.get("/v1/traces", params={"project_id": "p1"})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1
        assert isinstance(data["items"], list)

    async def test_detail_found(self, client):
        c = await client.post("/v1/traces", json={
            "user_input": "detail test",
            "model_output": "detail ok",
            "model": "t2",
        })
        tid = c.json()["trace_id"]
        r = await client.get(f"/v1/traces/{tid}")
        assert r.status_code == 200
        assert r.json()["user_input"] == "detail test"

    async def test_detail_not_found(self, client):
        r = await client.get("/v1/traces/doesnotexist12345")
        assert r.status_code == 404


class TestMockLLM:
    async def test_health(self):
        from app.services.mock_llm import app as mock_app
        from httpx import AsyncClient, ASGITransport

        t = ASGITransport(app=mock_app)
        async with AsyncClient(transport=t, base_url="http://test") as c:
            r = await c.get("/health")
            assert r.status_code == 200

    async def test_chat(self):
        from app.services.mock_llm import app as mock_app
        from httpx import AsyncClient, ASGITransport

        t = ASGITransport(app=mock_app)
        async with AsyncClient(transport=t, base_url="http://test") as c:
            r = await c.post("/v1/chat/completions", json={
                "model": "t",
                "messages": [{"role": "user", "content": "退款怎么退？"}],
                "stream": False,
            })
            assert r.status_code == 200
            data = r.json()
            assert "choices" in data
            assert "退款" in data["choices"][0]["message"]["content"]
            assert "usage" in data

    async def test_chat_streaming(self):
        from app.services.mock_llm import app as mock_app
        from httpx import AsyncClient, ASGITransport

        t = ASGITransport(app=mock_app)
        async with AsyncClient(transport=t, base_url="http://test") as c:
            r = await c.post("/v1/chat/completions", json={
                "model": "t",
                "messages": [{"role": "user", "content": "hi"}],
                "stream": True,
            })
            assert r.status_code == 200
            text = r.text
            assert "data:" in text
            assert "[DONE]" in text

    async def test_keyword_triggers(self):
        from app.services.mock_llm import _pick_response

        assert "7天" in _pick_response("我要退款")
        assert "会员" in _pick_response("会员等级？")
        assert "安全规范" in _pick_response("这是危险内容")
