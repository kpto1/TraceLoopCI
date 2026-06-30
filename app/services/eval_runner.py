import time
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import MOCK_LLM_URL
from app.services.evaluators import EVALUATORS
from app.models.golden import GoldenCase, GoldenDataset, EvalRun

logger = logging.getLogger("traceloop.eval")


async def run_eval(
    session: AsyncSession,
    dataset_id: int,
    model: str = "deepseek-chat",
    llm_target_url: Optional[str] = None,
    is_baseline: bool = False,
) -> dict:
    """Run all golden cases in a dataset through the configured LLM and evaluate."""
    target = llm_target_url or f"{MOCK_LLM_URL}/v1/chat/completions"
    t0 = time.monotonic()

    # Load cases
    from sqlalchemy import select
    result = await session.execute(
        select(GoldenCase).where(GoldenCase.dataset_id == dataset_id)
    )
    cases = list(result.scalars().all())

    if not cases:
        raise ValueError(f"No golden cases in dataset {dataset_id}")

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
    passed = 0
    costs = []
    latencies = []

    async with httpx.AsyncClient(timeout=120.0) as client:
        for case in cases:
            result_entry = await _eval_one(client, target, model, case)
            per_case.append(result_entry)

            if result_entry["overall_passed"]:
                passed += 1
            if result_entry.get("cost"):
                costs.append(result_entry["cost"])
            if result_entry.get("latency_ms"):
                latencies.append(result_entry["latency_ms"])

    total_time = (time.monotonic() - t0) * 1000

    # Compute aggregate
    failed = len(cases) - passed
    overall_score = int((passed / len(cases)) * 100) if cases else 0
    total_cost = sum(costs)
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else None

    run.status = "completed"
    run.passed = passed
    run.failed = failed
    run.overall_score = overall_score
    run.cost_total = int(total_cost * 1_000_000)  # micro-units
    run.latency_p95_ms = p95_latency
    run.per_case_results = per_case
    run.summary = {
        "total_time_ms": int(total_time),
        "avg_cost": round(total_cost / len(cases), 6) if cases else 0,
    }

    await session.commit()

    return {
        "run_id": run.id,
        "dataset_id": dataset_id,
        "model": model,
        "total_cases": len(cases),
        "passed": passed,
        "failed": failed,
        "overall_score": overall_score,
        "total_cost": round(total_cost, 6),
        "p95_latency_ms": p95_latency,
        "per_case": per_case,
    }


async def _eval_one(client, target_url, model, case) -> dict:
    """Run one golden case: call LLM → run all evaluators → return results."""
    t_start = time.monotonic()

    # Call LLM
    try:
        resp = await client.post(target_url, json={
            "model": model,
            "messages": [{"role": "user", "content": case.input_text}],
            "temperature": 0,
            "stream": False,
        })
        if resp.status_code != 200:
            return {
                "case_id": case.id,
                "input_text": case.input_text[:100],
                "overall_passed": False,
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
            "error": str(e),
        }

    elapsed = (time.monotonic() - t_start) * 1000
    cost = (tokens / 1_000_000) * 1.0  # $1/M tokens

    # Run evaluators
    golden = {
        "input_text": case.input_text,
        "expected_keywords": case.expected_keywords or [],
        "forbidden_keywords": case.forbidden_keywords or [],
        "expected_json_schema": case.expected_json_schema,
    }

    eval_results = {}
    for name, mod in EVALUATORS.items():
        try:
            eval_results[name] = await mod.evaluate(golden, output)
        except Exception:
            eval_results[name] = {
                "eval_type": name, "passed": False, "score": 0.0,
                "details": {"error": "Evaluator crashed"},
            }

    all_passed = all(r.get("passed", False) for r in eval_results.values())

    return {
        "case_id": case.id,
        "input_text": case.input_text[:200],
        "model_output": output[:500],
        "tokens": tokens,
        "cost": cost,
        "latency_ms": int(elapsed),
        "overall_passed": all_passed,
        "evaluators": eval_results,
    }
