"""Shared report contract for API and commit-local CLI evaluation."""

import hashlib
import json
import math

from app.services.evaluators import EVALUATORS
from app.services.evaluators.llm_judge import JUDGE_MODEL, JUDGE_PROMPT


def fingerprint(cases):
    return hashlib.sha256(
        json.dumps(cases, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()


async def evaluate_output(case, output, require_real_judge=True):
    results = {}
    for name, evaluator in EVALUATORS.items():
        try:
            results[name] = await evaluator.evaluate(case, output)
        except Exception:
            results[name] = {
                "passed": False,
                "state": "evaluation_error",
                "details": {"error": "Evaluator failed"},
            }
    missing = [doc for doc in case.get("must_cite_docs", []) if doc not in output]
    results["citations"] = {"passed": not missing, "details": {"missing": missing}}
    states = [r.get("state") for r in results.values()]
    degraded = any(r.get("details", {}).get("judge_model") == "mock" for r in results.values())
    error = "evaluation_error" in states
    passed = all(r.get("passed", False) for r in results.values())
    return {
        "overall_passed": passed and not error and not (require_real_judge and degraded),
        "state": "evaluation_error"
        if error
        else "degraded"
        if degraded
        else "passed"
        if passed
        else "failed",
        "model_output": output,
        "evaluators": results,
    }


def report(
    cases, results, revision="", baseline=None, min_score=80, max_drop=0, require_real_judge=True
):
    score = 100 * sum(r["overall_passed"] for r in results) / len(results) if results else 0
    dataset_hash = fingerprint(cases)
    errors = sum(r.get("state") == "evaluation_error" for r in results)
    degraded = sum(r.get("state") == "degraded" for r in results)
    evaluation_config = {
        "judge_model": JUDGE_MODEL,
        "judge_prompt_hash": fingerprint(JUDGE_PROMPT),
        "real_judge_required": require_real_judge,
        "evaluator_contract": 1,
    }
    reasons = []
    if not results:
        reasons.append("Dataset is empty")
    if errors:
        reasons.append("Evaluation infrastructure failed")
    if require_real_judge and degraded:
        reasons.append("Real judge required but unavailable")
    if score < min_score:
        reasons.append("Score below minimum")
    comparison = None
    if baseline is not None:
        if not baseline.get("gate_passed"):
            reasons.append("Baseline did not pass its gate")
        elif baseline.get("evaluation_config") != evaluation_config:
            reasons.append("Baseline evaluation configuration differs")
        elif baseline.get("dataset_hash") != dataset_hash:
            reasons.append("Baseline dataset differs; establish a new reviewed baseline")
        elif baseline.get("evaluation_errors") or (
            require_real_judge and baseline.get("degraded_cases")
        ):
            reasons.append("Baseline is not valid")
        else:
            delta = score - baseline["overall_score"]
            old = {str(r["case_id"]): r for r in baseline["per_case"]}
            regressed = [
                r["case_id"]
                for r in results
                if old.get(str(r["case_id"]), {}).get("overall_passed") and not r["overall_passed"]
            ]
            comparison = {"score_delta": delta, "regressed_cases": regressed}
            if delta < -max_drop or regressed:
                reasons.append("Behavior regressed against baseline")
    latencies = sorted(r["latency_ms"] for r in results if "latency_ms" in r)
    return {
        "evaluation_config": evaluation_config,
        "revision": revision,
        "dataset_hash": dataset_hash,
        "total_cases": len(results),
        "passed": sum(r["overall_passed"] for r in results),
        "failed": sum(not r["overall_passed"] for r in results),
        "overall_score": round(score, 2),
        "evaluation_errors": errors,
        "degraded_cases": degraded,
        "gate_passed": not reasons,
        "gate_reasons": reasons,
        "comparison": comparison,
        "p95_latency_ms": latencies[max(0, math.ceil(len(latencies) * 0.95) - 1)]
        if latencies
        else None,
        "total_cost": None,
        "cost_note": "Not measured; provider billing is authoritative",
        "per_case": results,
    }
