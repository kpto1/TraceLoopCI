import asyncio
import json
import os
import subprocess
import sys
from unittest.mock import AsyncMock, patch

import fakeredis.aioredis
import httpx
import pytest
from sqlalchemy import select

from app import config
from app.database import async_session
from app.models.trace import Span, Trace
from app.services.gate import evaluate_output, report
from app.services.trace_writer import _batch_write, _ensure_group, consume_entries


async def test_auth_and_validation(client, monkeypatch):
    monkeypatch.setattr(config, "API_KEY", "test-private-key")
    assert (await client.get("/v1/traces")).status_code == 401
    headers = {"X-API-Key": "test-private-key"}
    assert (await client.get("/v1/traces", headers=headers)).status_code == 200
    assert (
        await client.post("/v1/traces", headers=headers, json={"tokens_total": -2})
    ).status_code == 422
    assert (
        await client.post("/v1/traces", headers=headers, content=b"x" * 1048577)
    ).status_code == 413


async def test_enqueue_identity_and_span_idempotency():
    from app.services.trace_writer import enqueue_trace

    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    with (
        patch("app.services.trace_writer._redis", AsyncMock(return_value=r)),
        patch.object(r, "aclose", AsyncMock()),
    ):
        tid = await enqueue_trace({"user_input": "q", "spans": [{"span_type": "retrieval"}]})
    envelope = (await r.xrange(config.REDIS_STREAM_NAME))[0][1]
    data = json.loads(envelope["data"])
    assert data["trace_id"] == tid
    await _batch_write(async_session, [data, data])
    async with async_session() as session:
        trace = await session.scalar(select(Trace).where(Trace.trace_id == tid))
        spans = (await session.scalars(select(Span).where(Span.trace_id_fk == trace.id))).all()
        assert len(spans) == 1
    await r.aclose()


async def test_pending_retry_and_poison_preservation():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await _ensure_group(r)
    mid = await r.xadd(
        config.REDIS_STREAM_NAME,
        {"data": json.dumps({"trace_id": "pending-test", "user_input": "retry"})},
    )
    entries = (
        await r.xreadgroup(config.REDIS_CONSUMER_GROUP, "one", {config.REDIS_STREAM_NAME: ">"})
    )[0][1]
    with patch(
        "app.services.trace_writer._batch_write",
        AsyncMock(side_effect=RuntimeError("db unavailable")),
    ):
        with pytest.raises(RuntimeError):
            await consume_entries(r, async_session, entries)
    assert (await r.xpending(config.REDIS_STREAM_NAME, config.REDIS_CONSUMER_GROUP))["pending"] == 1
    reclaimed = await r.xautoclaim(config.REDIS_STREAM_NAME, config.REDIS_CONSUMER_GROUP, "two", 0)
    await consume_entries(r, async_session, reclaimed[1])
    assert await r.xrange(config.REDIS_STREAM_NAME, min=mid, max=mid) == []
    bad = await r.xadd(config.REDIS_STREAM_NAME, {"data": "invalid"})
    entries = (
        await r.xreadgroup(config.REDIS_CONSUMER_GROUP, "two", {config.REDIS_STREAM_NAME: ">"})
    )[0][1]
    await consume_entries(r, async_session, entries)
    assert (await r.xrange(config.REDIS_STREAM_NAME + ":dead"))[0][1]["source_id"] == bad
    await r.aclose()


@pytest.mark.skipif(
    not os.getenv("TEST_REAL_REDIS"), reason="Real Redis enabled in CI integration job"
)
async def test_real_redis_consumer_round_trip():
    from app.services.trace_writer import enqueue_trace, run_consumer

    task = asyncio.create_task(run_consumer(async_session))
    try:
        tid = await enqueue_trace({"user_input": "real redis"})
        for _ in range(100):
            async with async_session() as session:
                if await session.scalar(select(Trace.id).where(Trace.trace_id == tid)):
                    return
            await asyncio.sleep(0.05)
        pytest.fail("Trace never persisted")
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def test_stream_delivers_before_upstream_finishes():
    from app.services.stream_proxy import stream_response

    release = asyncio.Event()

    class Stream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b'data: {"choices":[{"delta":{"content":"first"}}]}\n\n'
            await release.wait()
            yield b"data: [DONE]\n\n"

    upstream = httpx.AsyncClient(
        transport=httpx.MockTransport(lambda req: httpx.Response(200, stream=Stream()))
    )
    persist = AsyncMock()
    with (
        patch("app.services.stream_proxy.get_client", AsyncMock(return_value=upstream)),
        patch("app.services.stream_proxy.persist", persist),
    ):
        response = await stream_response(
            "http://test/v1/chat/completions", {}, {"messages": [{"role": "user", "content": "q"}]}
        )
        first = await asyncio.wait_for(anext(response.body_iterator), 1)
        assert b"first" in first
        assert not release.is_set()
        release.set()
        async for _ in response.body_iterator:
            pass
        assert persist.call_args.args[0]["model_output"] == "first"
        assert persist.call_args.args[0]["status"] == "success"
    await upstream.aclose()


async def test_stream_upstream_failure_is_not_success():
    from fastapi import HTTPException

    from app.services.stream_proxy import stream_response

    upstream = httpx.AsyncClient(transport=httpx.MockTransport(lambda req: httpx.Response(401)))
    with (
        patch("app.services.stream_proxy.get_client", AsyncMock(return_value=upstream)),
        patch("app.services.stream_proxy.persist", AsyncMock()) as persist,
    ):
        with pytest.raises(HTTPException) as error:
            await stream_response("http://test", {}, {"messages": []})
        assert error.value.status_code == 502
        assert persist.call_args.args[0]["status"] == "error"
    await upstream.aclose()


async def test_real_judge_failure_fails_closed(monkeypatch):
    from app.services.evaluators import llm_judge

    monkeypatch.setattr(llm_judge, "JUDGE_API_KEY", "test")
    with patch(
        "app.services.evaluators.llm_judge.httpx.AsyncClient", side_effect=RuntimeError("offline")
    ):
        result = await evaluate_output({"expected_keywords": ["yes"]}, "yes")
    assert result["state"] == "evaluation_error"
    assert not result["overall_passed"]


async def test_missing_citations_and_degraded_judge():
    result = await evaluate_output({"must_cite_docs": ["policy-7"]}, "generic answer", False)
    assert not result["overall_passed"]
    result = await evaluate_output({}, "anything", True)
    assert result["state"] == "degraded"
    assert not result["overall_passed"]


def test_baseline_detects_regression_even_above_absolute_threshold():
    cases = [{"id": i} for i in range(10)]
    old = [{"case_id": i, "overall_passed": True, "state": "passed"} for i in range(10)]
    baseline = report(cases, old, "base")
    new = [dict(r) for r in old]
    new[0].update(overall_passed=False, state="failed")
    current = report(cases, new, "head", baseline)
    assert current["overall_score"] == 90
    assert current["comparison"]["regressed_cases"] == [0]
    assert not current["gate_passed"]
    assert not report(cases + [{"id": 10}], new, "head", baseline)["gate_passed"]


async def test_promote_preserves_context(client):
    trace = (
        await client.post(
            "/v1/traces",
            json={
                "user_input": "q",
                "system_prompt": "system",
                "metadata_extra": {"messages": [{"role": "user", "content": "q"}]},
            },
        )
    ).json()
    ds = (await client.post("/v1/datasets", json={"name": "context"})).json()
    response = await client.post(
        f"/v1/datasets/{ds['id']}/cases/from-trace/{trace['trace_id']}",
        json={"must_cite_docs": ["doc"]},
    )
    assert response.status_code == 200
    case = (await client.get(f"/v1/datasets/{ds['id']}")).json()["cases"][0]
    assert case["system_prompt"] == "system"
    assert case["messages"][0]["content"] == "q"
    assert case["must_cite_docs"] == ["doc"]


def test_cli_evaluates_changed_application(tmp_path):
    cases = tmp_path / "cases.json"
    cases.write_text('[{"id":1,"input_text":"q","expected_keywords":["correct"]}]')
    adapter = tmp_path / "candidate.py"
    adapter.write_text('def answer(case): return "correct"\n')
    base = tmp_path / "base.json"
    head = tmp_path / "head.json"
    cmd = [
        sys.executable,
        "-m",
        "app.cli",
        "--app-dir",
        str(tmp_path),
        "--adapter",
        "candidate:answer",
        "--cases",
        str(cases),
        "--allow-mock-judge",
    ]
    assert (
        subprocess.run(
            cmd + ["--revision", "base", "--output", str(base)], capture_output=True
        ).returncode
        == 0
    )
    adapter.write_text('def answer(case): return "broken-output-longer"\n')
    result = subprocess.run(
        cmd + ["--revision", "head", "--baseline", str(base), "--output", str(head)],
        capture_output=True,
    )
    assert result.returncode == 1
    data = json.loads(head.read_text(encoding="utf-8"))
    assert data["revision"] == "head"
    assert data["comparison"]["regressed_cases"] == [1]


def test_migration_preserves_existing_data(tmp_path):
    import sqlite3

    database = tmp_path / "migration.db"
    env = dict(os.environ, DATABASE_URL=f"sqlite+aiosqlite:///{database.as_posix()}")
    for revision in ["0001", "head", "head"]:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision], env=env, capture_output=True
        )
        assert result.returncode == 0, result.stderr.decode(errors="replace")
        with sqlite3.connect(database) as connection:
            if revision == "0001":
                connection.execute("INSERT INTO golden_datasets (id,name) VALUES (1,'preserved')")
            else:
                assert (
                    connection.execute("SELECT name FROM golden_datasets WHERE id=1").fetchone()[0]
                    == "preserved"
                )
                assert "messages" in {
                    r[1] for r in connection.execute("PRAGMA table_info(golden_cases)")
                }
