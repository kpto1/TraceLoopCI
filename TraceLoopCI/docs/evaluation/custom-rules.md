# 自定义评测规则

内置的 3 个评测器不够用时，可以自己写。评测器接口简单，基本上就是一个函数。

## 评测器接口

你的评测器是一个 Python `async def` 函数，接受两个参数，返回一个 dict：

```python
async def evaluate(golden_case: GoldenCase, model_output: str) -> dict:
    """
    参数:
      golden_case: SQLAlchemy model 实例
        - golden_case.input_text: 用户输入
        - golden_case.expected_keywords: 期望关键词列表
        - golden_case.forbidden_keywords: 禁止词列表
        - golden_case.expected_json_schema: JSON Schema（可选）
        - golden_case.must_cite_docs: 必须引用的文档
        - golden_case.tags: 标签
        - golden_case.notes: 备注
      model_output: 模型生成的文本

    返回:
      dict 必须包含:
        - eval_type: str    # 评测器标识
        - passed: bool      # 是否通过
        - score: float      # 0.0 ~ 1.0
        - details: dict     # 详细说明（可选）
    """
    pass
```

## 注册评测器

编辑 `app/services/evaluators/__init__.py`：

```python
from . import keyword_eval, json_eval, llm_judge
from . import regex_eval  # 你的新评测器

EVALUATORS = {
    "keyword": keyword_eval,
    "json_schema": json_eval,
    "llm_judge": llm_judge,
    "regex": regex_eval,   # 注册到这里
}
```

评测器会自动被 `eval_runner.py` 的 `run_eval()` 遍历执行。每个 case 会执行所有注册的评测器，结果汇总到 `per_case_results`。

## 示例：正则表达式评测器

场景：输出必须匹配特定格式（如订单号、邮箱、电话号码）。

```python
# app/services/evaluators/regex_eval.py
import re
from app.models.golden import GoldenCase


async def evaluate(golden_case: GoldenCase, model_output: str) -> dict:
    """
    检查模型输出是否匹配期望的正则表达式。
    在 golden case 的 notes 字段中书写正则表达式。
    """
    if not golden_case.notes:
        return {
            "eval_type": "regex_match",
            "passed": True,
            "score": 1.0,
            "details": {"message": "没有指定正则表达式，跳过"},
        }

    try:
        pattern = golden_case.notes.strip()
        match = re.search(pattern, model_output)
        passed = match is not None
        return {
            "eval_type": "regex_match",
            "passed": passed,
            "score": 1.0 if passed else 0.0,
            "details": {
                "pattern": pattern,
                "matched": match.group() if match else None,
            },
        }
    except re.error as e:
        return {
            "eval_type": "regex_match",
            "passed": False,
            "score": 0.0,
            "details": {"error": f"正则表达式错误: {str(e)}"},
        }
```

## 示例：长度评测器

```python
# app/services/evaluators/length_eval.py
from app.models.golden import GoldenCase


async def evaluate(golden_case: GoldenCase, model_output: str) -> dict:
    """
    检查模型输出长度是否在合理范围内。
    在 golden case 的 notes 中配置: "min:50,max:200"
    """
    notes = (golden_case.notes or "").strip()
    if not notes.startswith("min:"):
        return {"eval_type": "length_check", "passed": True, "score": 1.0,
                "details": {"message": "跳过"}}

    try:
        parts = notes.split(",")
        min_len = int(parts[0].split(":")[1])
        max_len = int(parts[1].split(":")[1]) if len(parts) > 1 else float("inf")

        actual_len = len(model_output)
        passed = min_len <= actual_len <= max_len

        return {
            "eval_type": "length_check",
            "passed": passed,
            "score": 1.0 if passed else 0.0,
            "details": {
                "min": min_len,
                "max": max_len,
                "actual": actual_len,
            },
        }
    except (ValueError, IndexError) as e:
        return {"eval_type": "length_check", "passed": False, "score": 0.0,
                "details": {"error": f"配置解析错误: {str(e)}"}}
```

## 如何测试

```python
# tests/test_custom_eval.py
import pytest
from app.services.evaluators import regex_eval
from app.models.golden import GoldenCase


@pytest.mark.asyncio
async def test_regex_eval_match():
    case = GoldenCase(notes=r"ORD-\d{6}")
    result = await regex_eval.evaluate(case, "您的订单号是 ORD-123456")
    assert result["passed"] is True
    assert result["score"] == 1.0
    assert result["details"]["matched"] == "ORD-123456"
```

## 注意事项

- 评测器函数在 `eval_runner._eval_one()` 中被依次调用，**不支持并行执行**。
- 如果评测器调用外部 API（如另一个 LLM），会显著增加评测总时间。
- 评测器抛出异常会导致整个 case 失败，但运行时已经在 try/except 中捕获，不会影响其它 case。
- 评测器注册后，所有历史评测会自动包含该评测器结果（只对新评测生效）。
- override 内置评测器时，同名 key 会覆盖原有实现。
