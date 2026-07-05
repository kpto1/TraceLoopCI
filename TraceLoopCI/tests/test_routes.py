"""Additional route tests to push coverage over 70%."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestTraceRoutesExtra:
    async def test_list_with_filters(self, client):
        r = await client.get("/v1/traces", params={"model": "gpt-4", "status": "success"})
        assert r.status_code == 200
        assert "items" in r.json()

    async def test_list_with_limit(self, client):
        r = await client.get("/v1/traces", params={"limit": 10, "offset": 5})
        assert r.status_code == 200

    async def test_list_defaults(self, client):
        r = await client.get("/v1/traces")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert data["limit"] == 50

    async def test_trace_by_id_without_spans(self, client):
        cr = await client.post("/v1/traces", json={
            "user_input": "test", "model_output": "ok", "model": "m"
        })
        tid = cr.json()["trace_id"]
        r = await client.get(f"/v1/traces/{tid}", params={"include_spans": False})
        assert r.status_code == 200
        assert "spans" not in r.json()


class TestDatasetRoutesExtra:
    async def test_get_dataset(self, client):
        r = await client.post("/v1/datasets", json={"name": "get-test"})
        ds_id = r.json()["id"]
        r2 = await client.get(f"/v1/datasets/{ds_id}")
        assert r2.status_code == 200
        assert r2.json()["name"] == "get-test"

    async def test_get_dataset_not_found(self, client):
        r = await client.get("/v1/datasets/99999")
        assert r.status_code == 404

    async def test_list_datasets_empty(self, client):
        r = await client.get("/v1/datasets", params={"project_id": "no-such-project"})
        assert r.status_code == 200
        assert r.json()["items"] == []

    async def test_eval_run_not_found(self, client):
        r = await client.get("/v1/eval/runs/99999")
        assert r.status_code == 404

    async def test_trigger_eval_missing_dataset(self, client):
        r = await client.post("/v1/eval/run", json={})
        assert r.status_code == 400


class TestProxyRouteExtra:
    async def test_proxy_no_key_when_disabled(self, client):
        # When API_KEY is empty, proxy accepts requests without auth
        r = await client.get("/proxy/health")
        assert r.status_code == 200
