import json
import uuid
import asyncio
import logging

import redis.asyncio as aioredis

from app.config import (
    REDIS_URL, REDIS_STREAM_NAME, REDIS_CONSUMER_GROUP,
    REDIS_BATCH_SIZE, REDIS_BATCH_TIMEOUT_MS,
)

logger = logging.getLogger("traceloop.writer")


async def _redis():
    return aioredis.from_url(REDIS_URL, decode_responses=True)


async def enqueue_trace(data: dict) -> str:
    trace_id = data.get("trace_id", uuid.uuid4().hex[:24])
    r = await _redis()
    payload = {
        "trace_id": trace_id,
        "data": json.dumps(data, ensure_ascii=False, default=str),
    }
    await r.xadd(REDIS_STREAM_NAME, payload, maxlen=100000)
    await r.aclose()
    return trace_id


async def _ensure_group(r):
    try:
        await r.xgroup_create(REDIS_STREAM_NAME, REDIS_CONSUMER_GROUP, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


async def run_consumer(db_session_factory):
    r = await _redis()
    await _ensure_group(r)
    logger.info("Trace consumer started (group=%s)", REDIS_CONSUMER_GROUP)

    while True:
        try:
            messages = await r.xreadgroup(
                groupname=REDIS_CONSUMER_GROUP,
                consumername="worker-1",
                streams={REDIS_STREAM_NAME: ">"},
                count=REDIS_BATCH_SIZE,
                block=REDIS_BATCH_TIMEOUT_MS,
            )

            if not messages:
                continue

            batch = []
            ids = []
            for _, entries in messages:
                for msg_id, data in entries:
                    if not data or "data" not in data:
                        await r.xack(REDIS_STREAM_NAME, REDIS_CONSUMER_GROUP, msg_id)
                        continue
                    try:
                        batch.append(json.loads(data["data"]))
                        ids.append(msg_id)
                    except json.JSONDecodeError:
                        logger.warning("Bad JSON in stream msg %s", msg_id)
                        await r.xack(REDIS_STREAM_NAME, REDIS_CONSUMER_GROUP, msg_id)

            if batch:
                await _batch_write(db_session_factory, batch)
                for msg_id in ids:
                    await r.xack(REDIS_STREAM_NAME, REDIS_CONSUMER_GROUP, msg_id)

        except aioredis.ConnectionError:
            logger.warning("Redis gone, reconnecting...")
            await asyncio.sleep(5)
            r = await _redis()
            await _ensure_group(r)
        except Exception:
            logger.exception("Consumer error")
            await asyncio.sleep(1)


async def _batch_write(factory, batch: list[dict]):
    from app.models.trace import Trace
    from datetime import datetime, timezone

    async with factory() as session:
        traces = []
        for d in batch:
            traces.append(Trace(
                trace_id=d.get("trace_id", uuid.uuid4().hex[:24]),
                project_id=d.get("project_id", "default"),
                user_input=d.get("user_input", ""),
                system_prompt=d.get("system_prompt"),
                model=d.get("model", "unknown"),
                provider=d.get("provider"),
                temperature=d.get("temperature"),
                max_tokens=d.get("max_tokens"),
                model_output=d.get("model_output"),
                tokens_prompt=d.get("tokens_prompt", 0),
                tokens_completion=d.get("tokens_completion", 0),
                tokens_total=d.get("tokens_total", 0),
                cost=d.get("cost", 0.0),
                latency_ms=d.get("latency_ms"),
                ttft_ms=d.get("ttft_ms"),
                status=d.get("status", "success"),
                error_message=d.get("error_message"),
                tags=d.get("tags", []),
                metadata_extra=d.get("metadata_extra", {}),
                created_at=datetime.now(timezone.utc),
            ))
        session.add_all(traces)
        await session.commit()
