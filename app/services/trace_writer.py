"""At-least-once delivery with pending recovery and idempotent writes."""

import asyncio
import json
import logging
import socket
import uuid

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.config import REDIS_CONSUMER_GROUP, REDIS_STREAM_NAME, REDIS_URL

logger = logging.getLogger(__name__)
HEARTBEAT = "traceloop:writer:heartbeat"


async def _redis():
    return aioredis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=3)


async def enqueue_trace(data: dict) -> str:
    data = dict(data)
    data["trace_id"] = data.get("trace_id") or uuid.uuid4().hex[:24]
    r = await _redis()
    try:
        await r.xadd(REDIS_STREAM_NAME, {"data": json.dumps(data, ensure_ascii=False, default=str)})
    finally:
        await r.aclose()
    return data["trace_id"]


async def _ensure_group(r):
    try:
        await r.xgroup_create(REDIS_STREAM_NAME, REDIS_CONSUMER_GROUP, id="0", mkstream=True)
    except aioredis.ResponseError as exc:
        if "BUSYGROUP" not in str(exc):
            raise


async def _batch_write(factory, batch):
    from app.models.trace import Trace
    from app.schemas import TraceInput
    from app.services.trace_service import create_trace

    for raw in batch:
        data = TraceInput.model_validate(raw).model_dump(exclude_none=True)
        async with factory() as session:
            existing = await session.scalar(
                select(Trace.id).where(Trace.trace_id == data["trace_id"])
            )
            if existing:
                continue
            try:
                await create_trace(session=session, **data)
            except IntegrityError:
                await session.rollback()
                if not await session.scalar(
                    select(Trace.id).where(Trace.trace_id == data["trace_id"])
                ):
                    raise


async def consume_entries(r, factory, entries):
    for msg_id, envelope in entries:
        try:
            data = json.loads(envelope["data"])
            await _batch_write(factory, [data])
        except (KeyError, ValueError):
            await r.xadd(
                REDIS_STREAM_NAME + ":dead", {"source_id": msg_id, "payload": json.dumps(envelope)}
            )
        # DB/transport exceptions propagate: message remains pending for retry.
        async with r.pipeline(transaction=True) as pipe:
            pipe.xack(REDIS_STREAM_NAME, REDIS_CONSUMER_GROUP, msg_id)
            pipe.xdel(REDIS_STREAM_NAME, msg_id)
            await pipe.execute()


async def run_consumer(db_session_factory):
    worker = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
    r = await _redis()
    cursor = "0-0"
    try:
        while True:
            try:
                await _ensure_group(r)
                await r.set(HEARTBEAT, worker, ex=30)
                reclaimed = await r.xautoclaim(
                    REDIS_STREAM_NAME,
                    REDIS_CONSUMER_GROUP,
                    worker,
                    min_idle_time=10000,
                    start_id=cursor,
                    count=100,
                )
                cursor = reclaimed[0]
                await consume_entries(r, db_session_factory, reclaimed[1])
                groups = await r.xreadgroup(
                    REDIS_CONSUMER_GROUP, worker, {REDIS_STREAM_NAME: ">"}, count=100, block=1000
                )
                for _, entries in groups:
                    await consume_entries(r, db_session_factory, entries)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Writer failed; pending messages will be retried")
                await asyncio.sleep(2)
    finally:
        await r.aclose()
