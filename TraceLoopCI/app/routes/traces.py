import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.config import API_KEY
from app.services.trace_service import (
    create_trace, create_trace_async, get_traces,
    get_trace_by_id, get_trace_with_spans, get_trace_count,
)

logger = logging.getLogger("traceloop.api")
router = APIRouter(prefix="/v1", tags=["traces"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def check_api_key(key: Optional[str] = Security(api_key_header)):
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return key or "anonymous"


@router.post("/traces")
async def ingest_trace(
    data: dict,
    session: AsyncSession = Depends(get_session),
    _key: str = Depends(check_api_key),
):
    try:
        trace = await create_trace(
            session=session,
            user_input=data.get("user_input", data.get("input", "")),
            model=data.get("model", "unknown"),
            model_output=data.get("model_output", data.get("output")),
            system_prompt=data.get("system_prompt"),
            provider=data.get("provider"),
            temperature=data.get("temperature"),
            max_tokens=data.get("max_tokens"),
            tokens_prompt=data.get("tokens_prompt", 0),
            tokens_completion=data.get("tokens_completion", 0),
            tokens_total=data.get("tokens_total", 0),
            cost=data.get("cost", 0.0),
            latency_ms=data.get("latency_ms"),
            ttft_ms=data.get("ttft_ms"),
            status=data.get("status", "success"),
            error_message=data.get("error_message"),
            project_id=data.get("project_id", "default"),
            tags=data.get("tags"),
            metadata_extra=data.get("metadata_extra"),
            spans=data.get("spans"),
        )
        return {"status": "ok", "trace_id": trace.trace_id}
    except Exception as e:
        logger.exception("Failed to ingest trace")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/traces/async")
async def ingest_trace_async(
    data: dict,
    _key: str = Depends(check_api_key),
):
    try:
        return await create_trace_async(data)
    except Exception as e:
        logger.exception("Failed to enqueue trace")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/traces")
async def list_traces(
    project_id: str = Query("default"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    model: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
    _key: str = Depends(check_api_key),
):
    traces = await get_traces(session, project_id, limit, offset, model, status)
    total = await get_trace_count(session, project_id, model, status)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "trace_id": t.trace_id,
                "project_id": t.project_id,
                "user_input": t.user_input[:200] if t.user_input else None,
                "model_output": t.model_output[:200] if t.model_output else None,
                "model": t.model,
                "provider": t.provider,
                "tokens_total": t.tokens_total,
                "cost": round(t.cost, 6) if t.cost else 0,
                "latency_ms": t.latency_ms,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in traces
        ],
    }


@router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: str,
    include_spans: bool = Query(True),
    session: AsyncSession = Depends(get_session),
    _key: str = Depends(check_api_key),
):
    trace = (
        await get_trace_with_spans(session, trace_id)
        if include_spans
        else await get_trace_by_id(session, trace_id)
    )
    if not trace:
        raise HTTPException(status_code=404, detail=f"Trace {trace_id} not found")

    result = {
        "trace_id": trace.trace_id,
        "project_id": trace.project_id,
        "user_input": trace.user_input,
        "system_prompt": trace.system_prompt,
        "model": trace.model,
        "provider": trace.provider,
        "temperature": trace.temperature,
        "max_tokens": trace.max_tokens,
        "model_output": trace.model_output,
        "tokens_prompt": trace.tokens_prompt,
        "tokens_completion": trace.tokens_completion,
        "tokens_total": trace.tokens_total,
        "cost": round(trace.cost, 6) if trace.cost else 0,
        "latency_ms": trace.latency_ms,
        "ttft_ms": trace.ttft_ms,
        "status": trace.status,
        "error_message": trace.error_message,
        "tags": trace.tags,
        "metadata_extra": trace.metadata_extra,
        "created_at": trace.created_at.isoformat() if trace.created_at else None,
    }

    if include_spans and trace.spans:
        result["spans"] = [
            {
                "span_id": s.span_id,
                "parent_span_id": s.parent_span_id,
                "span_type": s.span_type,
                "name": s.name,
                "input_data": s.input_data,
                "output_data": s.output_data,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                "duration_ms": s.duration_ms,
                "tokens_used": s.tokens_used,
                "cost": s.cost,
                "status": s.status,
                "error_message": s.error_message,
            }
            for s in trace.spans
        ]

    return result
