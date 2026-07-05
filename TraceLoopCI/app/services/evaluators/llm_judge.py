import json
import re
import logging

import httpx

from app.config import JUDGE_MODEL, JUDGE_API_KEY, JUDGE_BASE_URL

logger = logging.getLogger("traceloop.judge")

JUDGE_PROMPT = """你是一个严格的评测裁判。请根据以下标准打分（0-10分）。

用户问题：{input_text}
被评测的回答：{model_output}
期望包含的信息：{expected_keywords}
禁止出现的内容：{forbidden_keywords}

评分标准：
- 10分：完全满足期望，无禁止内容
- 7-9分：基本满足，有小瑕疵
- 4-6分：部分满足，有明显遗漏或偏差
- 1-3分：大多不满足
- 0分：完全错误或包含严重禁止内容

请严格打分，大多数回答应该落在5-8分区间。

请只输出以下JSON格式，不要输出其他内容：
{{"score": <整数0-10>, "reason": "<一句话理由>"}}"""


async def evaluate(golden_case: dict, model_output: str) -> dict:
    if not JUDGE_API_KEY:
        logger.warning("No JUDGE_API_KEY set — using mock judge")
        return _mock_judge(golden_case, model_output)

    prompt = JUDGE_PROMPT.format(
        input_text=golden_case.get("input_text", ""),
        model_output=model_output,
        expected_keywords=json.dumps(golden_case.get("expected_keywords", []), ensure_ascii=False),
        forbidden_keywords=json.dumps(golden_case.get("forbidden_keywords", []), ensure_ascii=False),
    )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{JUDGE_BASE_URL}/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {JUDGE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": JUDGE_MODEL,
                    "messages": [
                        {"role": "system", "content": "你是一个评测裁判。只输出JSON，不输出其他内容。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0,
                    "max_tokens": 200,
                },
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            result = _parse_judge_output(content)

    except Exception as e:
        logger.warning("Judge call failed: %s — falling back to mock", e)
        return _mock_judge(golden_case, model_output)

    raw_score = result.get("score", 5)
    return {
        "eval_type": "llm_judge",
        "passed": raw_score >= 6,
        "score": raw_score / 10.0,
        "details": {
            "judge_model": JUDGE_MODEL,
            "raw_score": raw_score,
            "reason": result.get("reason", ""),
        },
    }


def _parse_judge_output(text: str) -> dict:
    # Try direct JSON parse
    try:
        data = json.loads(text)
        return {"score": int(data["score"]), "reason": data.get("reason", "")}
    except (json.JSONDecodeError, KeyError, ValueError):
        pass

    # Try to extract JSON from markdown block
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            return {"score": int(data["score"]), "reason": data.get("reason", "")}
        except (json.JSONDecodeError, KeyError, ValueError):
            pass

    # Regex fallback: find "score": <number> or <number>分
    m = re.search(r'"score"\s*:\s*(\d+)', text)
    if m:
        return {"score": int(m.group(1)), "reason": text[:100]}

    m = re.search(r'(\d+)\s*分', text)
    if m:
        return {"score": int(m.group(1)), "reason": text[:100]}

    # Last resort: find any number 0-10
    numbers = re.findall(r'\b([0-9]|10)\b', text)
    if numbers:
        return {"score": int(numbers[0]), "reason": text[:100]}

    return {"score": 5, "reason": "无法解析裁判输出"}


def _mock_judge(golden_case: dict, model_output: str) -> dict:
    """Simple heuristic judge used when no real Judge API is available."""
    expected = golden_case.get("expected_keywords", []) or []
    forbidden = golden_case.get("forbidden_keywords", []) or []

    if not expected and not forbidden:
        return {
            "eval_type": "llm_judge",
            "passed": True,
            "score": 0.7,
            "details": {"judge_model": "mock", "raw_score": 7, "reason": "无断言规则，默认通过"},
        }

    hits = sum(1 for kw in expected if kw in model_output)
    expected_ratio = hits / len(expected) if expected else 1.0
    has_forbidden = any(kw in model_output for kw in forbidden)

    if has_forbidden:
        score = 2
    elif expected_ratio >= 0.9:
        score = 8
    elif expected_ratio >= 0.6:
        score = 6
    elif expected_ratio >= 0.3:
        score = 4
    else:
        score = 2

    return {
        "eval_type": "llm_judge",
        "passed": score >= 6,
        "score": score / 10.0,
        "details": {
            "judge_model": "mock",
            "raw_score": score,
            "reason": f"关键词命中率 {hits}/{len(expected)}",
        },
    }
