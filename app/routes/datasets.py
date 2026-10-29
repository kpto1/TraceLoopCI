import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.golden import EvalRun, GoldenCase, GoldenDataset
from app.schemas import CaseInput, DatasetInput, EvalInput
from app.security import check_key as check_key
from app.services.eval_runner import run_eval

logger = logging.getLogger("traceloop.datasets")
router = APIRouter(prefix="/v1", tags=["datasets"])

# -- Datasets --


@router.post("/datasets")
async def create_dataset(
    data: DatasetInput,
    session: AsyncSession = Depends(get_session),
    key: str = Depends(check_key),
):
    ds = GoldenDataset(
        name=data.get("name", "Unnamed"),
        description=data.get("description"),
        project_id=data.get("project_id", "default"),
    )
    session.add(ds)
    await session.commit()
    return {"id": ds.id, "name": ds.name}


@router.get("/datasets")
async def list_datasets(
    project_id: str = Query("default"),
    session: AsyncSession = Depends(get_session),
    key: str = Depends(check_key),
):
    result = await session.execute(
        select(GoldenDataset).where(GoldenDataset.project_id == project_id)
    )
    datasets = result.scalars().all()
    return {
        "items": [
            {
                "id": d.id,
                "name": d.name,
                "description": d.description,
                "created_at": d.created_at.isoformat(),
            }
            for d in datasets
        ]
    }


@router.get("/datasets/{id}")
async def get_dataset(
    id: int,
    session: AsyncSession = Depends(get_session),
    key: str = Depends(check_key),
):
    result = await session.execute(select(GoldenDataset).where(GoldenDataset.id == id))
    ds = result.scalar_one_or_none()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    cases_result = await session.execute(select(GoldenCase).where(GoldenCase.dataset_id == id))
    cases = cases_result.scalars().all()

    return {
        "id": ds.id,
        "name": ds.name,
        "description": ds.description,
        "case_count": len(cases),
        "cases": [
            {
                "id": c.id,
                "input_text": c.input_text,
                "messages": c.messages,
                "system_prompt": c.system_prompt,
                "must_cite_docs": c.must_cite_docs,
                "expected_keywords": c.expected_keywords,
                "forbidden_keywords": c.forbidden_keywords,
                "expected_json_schema": c.expected_json_schema,
                "source_trace_id": c.source_trace_id,
                "tags": c.tags,
            }
            for c in cases
        ],
    }


# -- Cases --


@router.post("/datasets/{dataset_id}/cases")
async def add_case(
    dataset_id: int,
    data: CaseInput,
    session: AsyncSession = Depends(get_session),
    key: str = Depends(check_key),
):
    if not await session.get(GoldenDataset, dataset_id):
        raise HTTPException(404, "Dataset not found")
    case = GoldenCase(
        dataset_id=dataset_id,
        input_text=data.get("input_text", ""),
        expected_keywords=data.get("expected_keywords", []),
        forbidden_keywords=data.get("forbidden_keywords", []),
        expected_json_schema=data.get("expected_json_schema"),
        must_cite_docs=data.get("must_cite_docs", []),
        source_trace_id=data.get("source_trace_id"),
        tags=data.get("tags", []),
        notes=data.get("notes"),
        messages=data.messages,
        system_prompt=data.system_prompt,
    )
    session.add(case)
    await session.commit()
    return {"id": case.id, "input_text": case.input_text[:100]}


@router.post("/datasets/{dataset_id}/cases/from-trace/{trace_id}")
async def add_case_from_trace(
    dataset_id: int,
    trace_id: str,
    data: CaseInput,
    session: AsyncSession = Depends(get_session),
    key: str = Depends(check_key),
):
    """Create a golden case from an existing trace."""
    from app.models.trace import Trace

    result = await session.execute(select(Trace).where(Trace.trace_id == trace_id))
    trace = result.scalar_one_or_none()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")

    if not await session.get(GoldenDataset, dataset_id):
        raise HTTPException(404, "Dataset not found")
    case = GoldenCase(
        dataset_id=dataset_id,
        source_trace_id=trace_id,
        must_cite_docs=data.must_cite_docs,
        input_text=data.input_text or trace.user_input or "",
        expected_keywords=data.get("expected_keywords", []),
        forbidden_keywords=data.get("forbidden_keywords", []),
        expected_json_schema=data.get("expected_json_schema"),
        tags=data.get("tags", []),
        notes=data.get("notes"),
        messages=data.messages or (trace.metadata_extra or {}).get("messages"),
        system_prompt=data.system_prompt or trace.system_prompt,
    )
    session.add(case)
    await session.commit()
    return {"id": case.id, "source_trace_id": trace_id}


# -- Eval --


@router.post("/eval/run")
async def trigger_eval(
    data: EvalInput,
    session: AsyncSession = Depends(get_session),
    key: str = Depends(check_key),
):
    dataset_id = data.get("dataset_id")
    if not dataset_id:
        raise HTTPException(status_code=400, detail="dataset_id required")

    model = data.get("model", "deepseek-chat")
    is_baseline = data.get("is_baseline", False)

    report = await run_eval(
        session=session,
        dataset_id=int(dataset_id),
        model=model,
        is_baseline=is_baseline,
        baseline_run_id=data.baseline_run_id,
        require_real_judge=data.require_real_judge,
        revision=data.revision,
        min_score=data.min_score,
        max_drop=data.max_drop,
    )
    return report


@router.get("/eval/runs")
async def list_eval_runs(
    dataset_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_session),
    key: str = Depends(check_key),
):
    stmt = select(EvalRun).order_by(EvalRun.created_at.desc()).limit(50)
    if dataset_id:
        stmt = stmt.where(EvalRun.dataset_id == dataset_id)
    result = await session.execute(stmt)
    runs = result.scalars().all()
    return {
        "items": [
            {
                "id": r.id,
                "dataset_id": r.dataset_id,
                "model": r.model,
                "is_baseline": bool(r.is_baseline),
                "status": r.status,
                "total_cases": r.total_cases,
                "passed": r.passed,
                "failed": r.failed,
                "overall_score": r.overall_score,
                "created_at": r.created_at.isoformat(),
            }
            for r in runs
        ]
    }


@router.get("/eval/runs/{run_id}")
async def get_eval_run(
    run_id: int,
    session: AsyncSession = Depends(get_session),
    key: str = Depends(check_key),
):
    result = await session.execute(select(EvalRun).where(EvalRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return {
        "id": run.id,
        "dataset_id": run.dataset_id,
        "model": run.model,
        "is_baseline": bool(run.is_baseline),
        "status": run.status,
        "total_cases": run.total_cases,
        "passed": run.passed,
        "failed": run.failed,
        "overall_score": run.overall_score,
        "cost_total": run.cost_total,
        "latency_p95_ms": run.latency_p95_ms,
        "summary": run.summary,
        "per_case": run.per_case_results,
        "created_at": run.created_at.isoformat(),
    }
