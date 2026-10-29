import asyncio
import json
import time
import uuid

import httpx
from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.database import async_session
from app.services.trace_collector import get_client
from app.services.trace_writer import _batch_write, enqueue_trace


async def persist(trace):
    try:
        await enqueue_trace(trace)
    except Exception:
        await _batch_write(async_session, [trace])


async def stream_response(target, headers, body):
    client = await get_client()
    start = time.monotonic()
    messages = body["messages"]
    trace = {
        "trace_id": uuid.uuid4().hex[:24],
        "model": body.get("model", "unknown"),
        "user_input": next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), ""
        ),
        "system_prompt": next(
            (m.get("content", "") for m in messages if m.get("role") == "system"), None
        ),
        "metadata_extra": {"messages": messages},
        "status": "success",
    }

    try:
        upstream = await client.send(
            client.build_request("POST", target, headers=headers, json=body), stream=True
        )
    except httpx.HTTPError:
        trace.update(
            status="error",
            error_message="Upstream connection failed",
            latency_ms=int((time.monotonic() - start) * 1000),
        )
        await persist(trace)
        raise HTTPException(502, "Upstream connection failed") from None
    if upstream.status_code != 200:
        await upstream.aclose()
        trace.update(
            status="error",
            error_message=f"Upstream returned {upstream.status_code}",
            latency_ms=int((time.monotonic() - start) * 1000),
        )
        await persist(trace)
        raise HTTPException(502, "Upstream stream failed")

    async def relay():
        output = []
        first = None
        completed = False
        try:
            async for line in upstream.aiter_lines():
                if line.startswith("data:"):
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        completed = True
                    else:
                        try:
                            chunk = json.loads(payload)
                            choices = chunk.get("choices", [])
                            delta = choices[0].get("delta", {}).get("content") if choices else None
                            if delta:
                                first = first or time.monotonic()
                                output.append(delta)
                            if chunk.get("error"):
                                trace["status"] = "error"
                            usage = chunk.get("usage") or {}
                            for src, dst in [
                                ("prompt_tokens", "tokens_prompt"),
                                ("completion_tokens", "tokens_completion"),
                                ("total_tokens", "tokens_total"),
                            ]:
                                if src in usage:
                                    trace[dst] = usage[src]
                        except (ValueError, TypeError, IndexError):
                            trace["status"] = "error"
                yield (line + "\n").encode()
        finally:
            await upstream.aclose()
            trace.update(
                model_output="".join(output),
                latency_ms=int((time.monotonic() - start) * 1000),
                ttft_ms=int((first - start) * 1000) if first else None,
            )
            if not completed:
                trace.update(status="error", error_message="Stream interrupted before DONE")
            task = asyncio.create_task(persist(trace))
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError:
                await task
                raise

    return StreamingResponse(
        relay(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
