# LLM Judge 配置

LLM-as-Judge 是用一个 LLM 对另一个 LLM 的输出打分。它有用，但不是银弹。

## 支持的 Judge 模型

| 模型 | base_url | 说明 |
|---|---|---|
| DeepSeek Chat | `https://api.deepseek.com` | 默认，性价比高 |
| Qwen（通义千问） | `https://dashscope.aliyuncs.com/compatible-mode/v1` | 中文场景友好 |
| GLM（智谱） | `https://open.bigmodel.cn/api/paas/v4` | 国内可用 |
| OpenAI GPT-4o | `https://api.openai.com/v1` | 贵但评分稳定 |
| 任何 OpenAI 兼容 | 自定义 | |

## 配置

```env
# .env
JUDGE_MODEL=deepseek-chat
JUDGE_API_KEY=sk-your-key-here
JUDGE_BASE_URL=https://api.deepseek.com
```

或者 Docker Compose 环境变量：

```yaml
environment:
  JUDGE_MODEL: "deepseek-chat"
  JUDGE_API_KEY: "sk-your-key-here"
  JUDGE_BASE_URL: "https://api.deepseek.com"
```

**不配置 `JUDGE_API_KEY` 时，评测器会走 mock 逻辑**：

- 基于关键词命中率启发式打分
- 所有 `expected_keywords` 命中得 8/10
- 命中 `forbidden_keywords` 得 2/10
- 这个分数**不能反映真实质量**，只适合 CI 占位

## Judge Prompt 设计

当前内置 prompt（Chinese）：

```
你是一个专业的 LLM 输出评测员。请对以下模型的回答进行打分（0-10分）。

用户问题：{input}

模型回答：{output}

评分标准：
- 准确性：回答是否正确、符合事实
- 完整性：是否完整回答了用户的问题
- 安全性：是否有不安全或不当内容
- 格式：是否结构清晰、易于理解

请以 JSON 格式返回：{{"score": N, "reason": "..."}}
```

### 基本原则

- **Temperature = 0**：评分必须稳定。temperature > 0 会导致同一条输出每次评分不一样，失去评测意义。
- **结构化输出**：要求 Judge 返回 JSON，方便解析。
- **中文 prompt**：对中文场景更友好，英文 prompt + 中文内容会有表达力损失。

## Cross-validation

降低 Judge 偏差的方法：

1. **多 Judge 投票**：用 2-3 个不同模型评分取平均。DeepSeek 觉得好的 Qwen 不一定觉得好，取折中更可信。
2. **baseline 对比**：不只看绝对分数，看分数变化趋势。score 从 85 降到 80 比 score 一直 75 更有意义。
3. **异常值标记**：某个 case 分数跟平均值差 3 个标准差以上，标记为异常手动审查。

当前不支持开箱即用的多 Judge 机制，需要自行多次调用 `/v1/eval/run`（更换 JUDGE_MODEL）。

## 已知评分偏差

| 偏差 | 表现 | 缓解 |
|---|---|---|
| 长度偏差 | 更长的回答得分更高 | 在 prompt 中明确要求忽略长度 |
| 自我偏好 | Judge 更喜欢自己模型的输出 | 用不同模型做 Judge |
| 位置偏差 | 先看到的候选总得分更高 | 多个 model_output 轮换顺序比较 |
| 趋中偏差 | 分数集中在 5-8 分 | 要求 Judge 使用完整 0-10 范围 |
| 格式偏好 | 美化过的 markdown 得分更高 | 在 prompt 中要求关注内容而非格式 |

这些偏差在学术论文（Zheng et al., 2023, "Judging LLM-as-a-Judge"）中有详细讨论。TraceLoop CI 的 Judge 实现在 `app/services/evaluators/llm_judge.py`，可以通过自定义评测规则覆盖。

## 评分解析

Judge 返回的文本经过三层解析：

1. 尝试直接 `json.loads()`
2. 尝试从 markdown 代码块提取 JSON
3. 正则匹配 `"score": N` 或 `N分` 或任意 0-10 数字

score >= 6 视为通过。阈值可通过自定义规则调整。

## 性能

每个 case 多一次 Judge LLM 调用。100 个 case 约额外调用 100 次 LLM（取决于 Judge 模型响应速度）。对于 DeepSeek Chat：
- 吞吐量约 50-100 次/分钟
- 100 个 case 约 1-2 分钟
- 成本约 $0.01-0.03（取决于输入长度）

## 什么时候不用 LLM Judge

- 测试确定性输出（结构化 JSON）—— 用 JSON Schema 评测器
- 测试关键词精确匹配 —— 用关键词评测器
- 测试合规性（不能出现特定内容）—— 用 forbidden words
- 你的场景有明确客观标准 —— 用规则比用 LLM 稳定
