"""Explicit opt-in live acceptance: synthetic data, at most 18 paid requests."""

import asyncio
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import httpx

from app.config import JUDGE_API_KEY, LLM_API_KEY
from app.services.eval_runner import _eval_one
from app.services.gate import evaluate_output, report


async def main():
    if not LLM_API_KEY or LLM_API_KEY != JUDGE_API_KEY:
        raise RuntimeError("Acceptance requires one configured account for cost tracking")
    headers = {"Authorization": f"Bearer {LLM_API_KEY}"}
    async with httpx.AsyncClient(timeout=120) as client:

        async def balance():
            response = await client.get("https://api.deepseek.com/user/balance", headers=headers)
            response.raise_for_status()
            rows = response.json()["balance_infos"]
            return Decimal(next(r["total_balance"] for r in rows if r["currency"] == "CNY"))

        before = await balance()
        cases, baseline, candidate = [], [], []
        samples = [
            ("2加3等于几？", "5"),
            ("中国的首都是哪里？", "北京"),
            ("水的化学式是什么？请只输出ASCII字符，不使用下标字符。", "H2O"),
            ("一周有几天？", "7"),
            ("英文cat的中文是什么？", "猫"),
            ("10减4等于几？", "6"),
        ]
        for i, (question, answer) in enumerate(samples):
            # Stop well below the user's 20 CNY ceiling; each bounded pair is tiny.
            if before - await balance() >= Decimal("1"):
                raise RuntimeError("Conservative 1 CNY acceptance stop reached")
            case = dict(
                id=i + 1,
                input_text=question,
                expected_keywords=[answer],
                forbidden_keywords=[],
                must_cite_docs=[],
                expected_json_schema=None,
                messages=None,
                system_prompt="只输出答案，不解释。数字使用阿拉伯数字。",
            )
            cases.append(case)
            good = await _eval_one(
                client,
                "https://api.deepseek.com/v1/chat/completions",
                "deepseek-flash",
                SimpleNamespace(**case),
                True,
            )
            baseline.append(good)
            bad = await evaluate_output(case, "不知道，无法提供答案。", True)
            bad.update(case_id=i + 1, input_text=question)
            candidate.append(bad)
            print(
                json.dumps(
                    {
                        "case": i + 1,
                        "generated_passed": good["overall_passed"],
                        "bad_answer_rejected": not bad["overall_passed"],
                        "judge_state": bad["state"],
                    }
                ),
                flush=True,
            )
        base = report(cases, baseline, revision="live-flash-baseline")
        regression = report(cases, candidate, revision="deliberately-wrong", baseline=base)
        spent = before - await balance()
        result = {
            "model": "deepseek-flash",
            "paid_requests_max": 18,
            "balance_decrease_cny": str(spent),
            "baseline": base,
            "regression": regression,
        }
        Path("../../outputs/deepseek-live-acceptance.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        assert base["gate_passed"], "Real baseline failed; inspect report"
        assert not regression["gate_passed"] and regression["comparison"]["regressed_cases"]
        assert not base["evaluation_errors"] and not regression["evaluation_errors"]
        assert not base["degraded_cases"] and not regression["degraded_cases"]
        print("Live acceptance passed; balance decrease CNY:", spent)


if __name__ == "__main__":
    asyncio.run(main())
