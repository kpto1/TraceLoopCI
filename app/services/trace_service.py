from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trace import Trace, Span
from app.services.trace_writer import enqueue_trace


async def create_trace(
    session: AsyncSession,
    *,
    user_input: str,
    model: str,
    model_output: Optional[str] = None,
    system_prompt: Optional[str] = None,
    provider: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    tokens_prompt: int = 0,
    tokens_completion: int = 0,
    tokens_total: int = 0,
    cost: float = 0.0,
    latency_ms: Optional[int] = None,
    ttft_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    project_id: str = "default",
    tags: Optional[list] = None,
    metadata_extra: Optional[dict] = None,
    spans: Optional[list[dict]] = None,
) -> Trace:
    trace = Trace(
        user_input=user_input,
        model=model,
        model_output=model_output,
        system_prompt=system_prompt,
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
        tokens_prompt=tokens_prompt,
        tokens_completion=tokens_completion,
        tokens_total=tokens_total,
        cost=cost,
        latency_ms=latency_ms,
        ttft_ms=ttft_ms,
        status=status,
        error_message=error_message,
        project_id=project_id,
        tags=tags or [],
        metadata_extra=metadata_extra or {},
        created_at=datetime.now(timezone.utc),
    )
    session.add(trace)
    await session.flush()

    if spans:
        for s in spans:
            session.add(Span(
                trace_id_fk=trace.id,
                span_type=s.get("span_type", "unknown"),
                name=s.get("name"),
                parent_span_id=s.get("parent_span_id"),
                input_data=s.get("input_data"),
                output_data=s.get("output_data"),
                started_at=s.get("started_at"),
                ended_at=s.get("ended_at"),
                duration_ms=s.get("duration_ms"),
                tokens_used=s.get("tokens_used", 0),
                cost=s.get("cost", 0.0),
                status=s.get("status", "success"),
                error_message=s.get("error_message"),
                metadata_extra=s.get("metadata_extra", {}),
            ))

    await session.commit()
    return trace


async def create_trace_async(data: dict) -> dict:
    trace_id = await enqueue_trace(data)
    return {"status": "received", "trace_id": trace_id}


async def get_traces(
    session: AsyncSession,
    project_id: str = "default",
    limit: int = 50,
    offset: int = 0,
    model: Optional[str] = None,
    status: Optional[str] = None,
) -> list[Trace]:
    stmt = select(Trace).where(Trace.project_id == project_id)
    if model:
        stmt = stmt.where(Trace.model == model)
    if status:
        stmt = stmt.where(Trace.status == status)
    stmt = stmt.order_by(Trace.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_trace_by_id(session: AsyncSession, trace_id: str) -> Optional[Trace]:
    result = await session.execute(
        select(Trace).where(Trace.trace_id == trace_id)
    )
    return result.scalar_one_or_none()


async def get_trace_with_spans(session: AsyncSession, trace_id: str) -> Optional[Trace]:
    from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(Trace)
        .options(selectinload(Trace.spans))
        .where(Trace.trace_id == trace_id)
    )
    return result.scalar_one_or_none()


async def get_trace_count(
    session: AsyncSession,
    project_id: str = "default",
    model: Optional[str] = None,
    status: Optional[str] = None,
) -> int:
    stmt = select(func.count(Trace.id)).where(Trace.project_id == project_id)
    if model:
        stmt = stmt.where(Trace.model == model)
    if status:
        stmt = stmt.where(Trace.status == status)
    result = await session.execute(stmt)
    return result.scalar() or 0
