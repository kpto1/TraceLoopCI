# 7 个评测维度详解

TraceLoop CI 运行评测时对每个 golden case 执行多个维度的检查。当前内置 3 个评测器，其余维度通过配置和数据字段支持。

## 内置评测器

### 1. 关键词断言（keyword_assertion）

**检查什么**：模型输出包含所有 `expected_keywords`，且不包含任何 `forbidden_keywords`。

**什么时候用**：输出中必须有/不能有特定词汇的场景，例如：
- 客服回复必须提到"退款"和"7天"
- 安全回复中不能出现"忽略指令"或"作为AI"

**实现**：不分大小写的子串匹配。

**评分**：通过(1.0) / 不通过(0.0)。所有期望词都出现且没有禁止词才算通过。

**局限**：
- 子串匹配天然有误报。"不能退款"包含"退款"，但它是禁止词，同时出现在期望词和禁止词时会额外检查。
- 语义近义词不匹配。"refund"匹配不到"退还"。
- 对大段输出做关键词匹配比较脆弱，建议跟 LLM Judge 配合使用。

### 2. JSON Schema 合规（json_schema）

**检查什么**：模型输出是合法 JSON，且（如果指定了 `expected_json_schema`）符合 JSON Schema 定义。

**什么时候用**：要求模型输出结构化 JSON 的场景，如：
- 函数调用参数
- 结构化数据提取
- API 响应生成

**实现**：先用 `json.loads()` 解析，再用 `jsonschema.validate()` 校验。输出如果不是 JSON 就算失败。

**局限**：
- JSON Schema 校验严格。多一个字段或少一个可选字段可能导致失败，取决于 schema 定义。
- 对于 markdown 代码块中的 JSON（```json ... ```），当前不会自动提取，需要自行处理。
- 底层依赖 `jsonschema` 库，对 Draft 4/7/2020-12 的支持取决于版本。

### 3. LLM-as-Judge（llm_judge）

**检查什么**：用另一个 LLM 对模型输出打分（0-10），评估整体质量。

**什么时候用**：以下场景最有效：
- 没有明确的正确答案时评估质量
- 客服对话的礼貌性和信息完整性
- 需要主观判断的评估（回答的语气、可读性）

**实现**：支持 DeepSeek、Qwen、GLM 和 OpenAI 兼容模型。详见 [LLM Judge 配置](llm-judge.md)。

**局限**：
- **评分偏差**：LLM Judge 有自己的偏好，可能更喜欢符合自身风格的回复。
- **成本**：每次评测调用 gold case 的模型 + Judge LLM，成本翻倍。
- **速度**：串行调用 Judge LLM，100 个 case 约需几分钟。
- Judge API key 未配置时会用 mock 评分（基于关键词命中率的启发式算法），**不能反映真实质量**。

## 通过 Golden Case 字段支持的维度

以下维度通过 `GoldenCase` 和 `EvalRun` 的现有字段支持，当前没有独立的评测器，而是通过数据模型和评测报告提供定量指标。

### 4. 文档引用准确性

**通过字段**：`must_cite_docs`（golden case）

**检查什么**：模型输出中包含了指定的文档引用。当前仅作为数据字段记录，需要结合关键词评测器使用。

**如果要做精确检查**：在 `expected_keywords` 中添加文档 ID 或引用标记。

### 5. 成本比较

**通过字段**：`cost_total`、`cost_change_pct`（EvalRun）

**检查什么**：对比不同模型或同一模型不同版本的成本变化。每次评测记录总体成本和与 baseline 的对比百分比。

**使用方式**：`GET /v1/eval/runs` 返回中包含 `cost_total` 和 `cost_change_pct`（跟前一次 baseline 比）。成本按 `$1/M tokens` 估算，实际成本取决于模型定价。

### 6. 延迟比较

**通过字段**：`latency_p95_ms`、`latency_change_ms`（EvalRun）

**检查什么**：评测中所有 case 的 P95 延迟，以及与 baseline 的差值。

**注意**：延迟包括 LLM 调用时间 + 网络开销。在 mock LLM 模式下的延迟数据没有参考价值。

### 7. Forbidden Words Detection

**通过字段**：`forbidden_keywords`（golden case）

**检查什么**：模型输出中没有出现禁止词。由关键词评测器覆盖。

## 评测报告聚合

单次评测的 `overall_score`（0-100）计算方式：

```
overall_score = (passed / total_cases) * 100
```

每个 case 的 `overall_passed` 判定：所有评测器都 `passed = true` 才算通过。只要有一个评测器失败，该 case 就算失败。

## 当前不支持（但计划中）

- 语义相似度（cosine similarity on embeddings）
- BLEU / ROUGE 分数
- 人工审核工作流
- 回归分析（自动检测 score 下降趋势）

评测器接口是开放的，以上维度可以通过[自定义规则](custom-rules.md)添加。
