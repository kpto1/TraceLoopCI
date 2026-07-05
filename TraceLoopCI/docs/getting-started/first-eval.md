# 第一个评测运行

这篇文章教你：创建数据集 -> 添加 golden case -> 运行评测 -> 在仪表盘查看结果。

## 前提

你已经完成了[快速开始](quickstart.md)，所有服务正常运行。

## 第一步：创建数据集

数据集是 golden case 的集合，每个 case 包含输入、期望关键词、禁止词等。

```bash
curl -X POST http://localhost:8000/v1/datasets \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -d '{
    "name": "客服退款场景",
    "description": "客服场景的退款政策回复评测",
    "project_id": "default"
  }'
```

返回：
```json
{"id": 1, "name": "客服退款场景"}
```

记下返回的 `id`，后面会用到。

## 第二步：添加 golden case

每个 case 包含：
- `input_text`：用户输入（评测时会发给模型）
- `expected_keywords`：期望在回答中出现的关键词
- `forbidden_keywords`：回答中绝不能出现的词
- `expected_json_schema`：可选，期望输出符合的 JSON Schema
- `must_cite_docs`：可选，必须引用的文档 ID

```bash
curl -X POST http://localhost:8000/v1/datasets/1/cases \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -d '{
    "input_text": "退款需要多久到账？",
    "expected_keywords": ["7天", "退款"],
    "forbidden_keywords": ["不能退款", "拒绝"],
    "tags": ["退款", "时效"]
  }'
```

再加一个：

```bash
curl -X POST http://localhost:8000/v1/datasets/1/cases \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -d '{
    "input_text": "VIP 会员有什么福利？",
    "expected_keywords": ["折扣", "会员"],
    "forbidden_keywords": ["收费", "额外费用"],
    "tags": ["会员", "权益"]
  }'
```

## 第三步：运行评测

```bash
curl -X POST http://localhost:8000/v1/eval/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -d '{
    "dataset_id": 1,
    "model": "deepseek-chat",
    "is_baseline": true
  }'
```

`is_baseline=true` 标记这次结果为基准线，后续评测可以对比。

返回类似：
```json
{
  "run_id": 1,
  "dataset_id": 1,
  "model": "deepseek-chat",
  "total_cases": 2,
  "passed": 2,
  "failed": 0,
  "overall_score": 85,
  "total_cost": 0.00021,
  "p95_latency_ms": 950,
  "per_case": [
    {
      "case_id": 1,
      "input_text": "退款需要多久到账？",
      "model_output": "我们的退款政策是 7 天内到账...",
      "overall_passed": true,
      "evaluators": {
        "keyword": {"passed": true, "score": 1.0},
        "json_schema": {"passed": true, "score": 1.0},
        "llm_judge": {"passed": true, "score": 0.8}
      }
    }
  ]
}
```

每次评测会调用 Mock LLM（`app/services/mock_llm.py`）为每个 case 生成回复。开发者环境默认使用 Mock LLM，不需要真实 API key。

## 第四步：查看评测历史

```bash
curl -H "X-API-Key: dev-api-key-change-in-production" \
  http://localhost:8000/v1/eval/runs
```

查看某次评测的完整结果：

```bash
curl -H "X-API-Key: dev-api-key-change-in-production" \
  http://localhost:8000/v1/eval/runs/1
```

## 从已有 trace 创建 golden case

如果已经有一条 trace 数据，可以直接从 trace 创建 golden case，省去手动输入：

```bash
curl -X POST http://localhost:8000/v1/datasets/1/cases/from-trace/{trace_id} \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -d '{"expected_keywords": ["退款", "7天"]}'
```

## 在仪表盘看结果

目前前端仅支持 trace 查看（`/traces` 和 `/traces/[id]`），评测结果需通过 API 获取。后续版本会加入评测仪表盘。

## 下一步

- 了解 [7 个评测维度](../evaluation/dimensions.md) 的详细说明
- 配置 [真实的 LLM Judge 评分器](../evaluation/llm-judge.md)
- 编写[自定义评测规则](../evaluation/custom-rules.md)
