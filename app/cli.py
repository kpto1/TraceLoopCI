"""Evaluate the checked-out application, without a remote TraceLoop deployment."""

import argparse
import asyncio
import importlib
import inspect
import json
import sys
import time
from pathlib import Path

from app.services.gate import evaluate_output, report


async def evaluate(adapter, cases, require_real):
    results = []
    for index, case in enumerate(cases):
        start = time.monotonic()
        try:
            output = adapter(case)
            if inspect.isawaitable(output):
                output = await asyncio.wait_for(output, timeout=120)
            if not isinstance(output, str):
                raise TypeError("Adapter must return a string")
            result = await evaluate_output(case, output, require_real)
        except Exception as exc:
            result = {
                "overall_passed": False,
                "state": "evaluation_error",
                "error": type(exc).__name__,
            }
        result.update(
            case_id=case.get("id", index + 1),
            input_text=case.get("input_text", ""),
            latency_ms=int((time.monotonic() - start) * 1000),
        )
        results.append(result)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-dir", default=".")
    parser.add_argument(
        "--adapter", required=True, help="module:function receiving a case dict and returning text"
    )
    parser.add_argument("--cases", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--baseline")
    parser.add_argument("--output", default="eval_report.json")
    parser.add_argument("--min-score", type=int, default=80)
    parser.add_argument("--max-drop", type=int, default=0)
    parser.add_argument(
        "--allow-mock-judge",
        action="store_true",
        help="Demo only: allow explicitly marked heuristic results",
    )
    args = parser.parse_args()
    try:
        sys.path.insert(0, str(Path(args.app_dir).resolve()))
        module, function = args.adapter.split(":", 1)
        adapter = getattr(importlib.import_module(module), function)
        cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
        if not isinstance(cases, list) or not cases:
            raise ValueError("Cases must be a nonempty array")
        baseline = (
            json.loads(Path(args.baseline).read_text(encoding="utf-8")) if args.baseline else None
        )
        results = asyncio.run(evaluate(adapter, cases, not args.allow_mock_judge))
        result = report(
            cases,
            results,
            args.revision,
            baseline,
            args.min_score,
            args.max_drop,
            not args.allow_mock_judge,
        )
    except Exception as exc:
        result = {
            "gate_passed": False,
            "evaluation_errors": 1,
            "gate_reasons": [f"Setup failed: {type(exc).__name__}"],
        }
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "per_case"}, ensure_ascii=True))
    return 0 if result["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
