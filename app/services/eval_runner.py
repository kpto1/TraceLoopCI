import logging
import time
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import LLM_API_KEY, LLM_BASE_URL
from app.models.golden import EvalRun, GoldenCase
from app.services.gate import evaluate_output
from app.services.gate import report as build_report

logger = logging.getLogger("traceloop.eval")


async def run_eval(
    session: AsyncSession,
    dataset_id: int,
    model: str = "deepseek-chat",
    llm_target_url: Optional[str] = None,
    is_baseline: bool = False,
    baseline_run_id: int | None = None,
    require_real_judge: bool = True,
    revision: str = "",
    min_score: int = 80,
    max_drop: int = 0,
) -> dict:
    """Run all golden cases in a dataset through the configured LLM and evaluate."""
    target = llm_target_url or f"{LLM_BASE_URL.rstrip(chr(47))}/v1/chat/completions"
    t0 = time.monotonic()

    # Load cases
    from sqlalchemy import select

    result = await session.execute(
        select(GoldenCase).where(GoldenCase.dataset_id == dataset_id).order_by(GoldenCase.id)
    )
    cases = list(result.scalars().all())

    if not cases:
        raise ValueError(f"No golden cases in dataset {dataset_id}")

    baseline = None
    if baseline_run_id:
        baseline_run = await session.get(EvalRun, baseline_run_id)
        if (
            not baseline_run
            or baseline_run.dataset_id != dataset_id
            or not baseline_run.is_baseline
        ):
            raise ValueError("Baseline must be a baseline run from this dataset")
        baseline = (baseline_run.summary or {}).get("report")
        if not baseline:
            raise ValueError("Legacy baseline has no reproducible report")
    snapshots = [
        {
            "id": c.id,
            "input_text": c.input_text,
            "expected_keywords": c.expected_keywords or [],
            "forbidden_keywords": c.forbidden_keywords or [],
            "expected_json_schema": c.expected_json_schema,
            "must_cite_docs": c.must_cite_docs or [],
            "messages": c.messages,
            "system_prompt": c.system_prompt,
        }
        for c in cases
    ]
    # Create eval run record
    run = EvalRun(
        dataset_id=dataset_id,
        model=model,
        is_baseline=1 if is_baseline else 0,
        status="running",
        total_cases=len(cases),
    )
    session.add(run)
    await session.commit()

    per_case = []
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            for case in cases:
                per_case.append(await _eval_one(client, target, model, case, require_real_judge))
    except BaseException:
        run.status = "failed"
        run.summary = {"error": "Evaluation interrupted before completion"}
        await session.commit()
        raise

    report = build_report(
        snapshots, per_case, revision, baseline, min_score, max_drop, require_real_judge
    )
    report.update(run_id=run.id, dataset_id=dataset_id, model=model)
    run.status = "failed" if report["evaluation_errors"] else "completed"
    run.passed = report["passed"]
    run.failed = report["failed"]
    run.overall_score = int(report["overall_score"])
    run.cost_total = None
    run.latency_p95_ms = report["p95_latency_ms"]
    run.per_case_results = per_case
    run.summary = {"report": report, "total_time_ms": int((time.monotonic() - t0) * 1000)}
    await session.commit()
    return report


async def _eval_one(client, target_url, model, case, require_real_judge=True) -> dict:
    """Run one golden case: call LLM → run all evaluators → return results."""
    t_start = time.monotonic()

    # Call LLM
    try:
        resp = await client.post(
            target_url,
            json={
                "model": model,
                "messages": case.messages
                or (
                    (
                        [{"role": "system", "content": case.system_prompt}]
                        if case.system_prompt
                        else []
                    )
                    + [{"role": "user", "content": case.input_text}]
                ),
                "temperature": 0,
                "stream": False,
            },
            headers={"Authorization": f"Bearer {LLM_API_KEY}"} if LLM_API_KEY else {},
        )
        if resp.status_code != 200:
            return {
                "case_id": case.id,
                "input_text": case.input_text[:100],
                "overall_passed": False,
                "state": "evaluation_error",
                "error": f"LLM returned {resp.status_code}",
            }
        data = resp.json()
        output = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens", 0)
    except Exception as e:
        return {
            "case_id": case.id,
            "input_text": case.input_text[:100],
            "overall_passed": False,
            "state": "evaluation_error",
            "error": type(e).__name__,
        }

    elapsed = (time.monotonic() - t_start) * 1000
    golden = {
        "input_text": case.input_text,
        "expected_keywords": case.expected_keywords or [],
        "forbidden_keywords": case.forbidden_keywords or [],
        "expected_json_schema": case.expected_json_schema,
        "must_cite_docs": case.must_cite_docs or [],
    }
    result = await evaluate_output(golden, output, require_real_judge)
    result.update(
        case_id=case.id, input_text=case.input_text, tokens=tokens, latency_ms=int(elapsed)
    )
    return result
