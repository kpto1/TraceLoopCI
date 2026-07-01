# 常见问题

## Q: 和 Langfuse 有什么区别？

Langfuse 是做 LLM 可观测的，你能看到每次调用发生了什么、花了多少钱、延迟多少。TraceLoop CI 在此基础上加了一层**回归测试**：

- Golden dataset 管理（定义什么是"对的答案"）
- 自动评测（关键词检查 / JSON Schema / LLM Judge）
- CI 集成（PR 提交时自动评测 + 评论）
- Baseline 对比（升级模型后回答变好了还是差了）

互补使用：Langfuse 看生产运行状态，TraceLoop CI 看发布前质量变化。

## Q: 支持哪些模型？

任何 OpenAI 兼容 API 的模型都支持：DeepSeek、Qwen、GLM、OpenAI、vLLM、Ollama。

非 OpenAI 格式的模型（如 Claude 的原生 API）需要自行适配，或者用直写方式跳过代理层：
```python
# 绕过 proxy，直接写 trace
POST /v1/traces  # 传入 user_input + model_output 就行
```

## Q: LLM-as-Judge 打分准吗？

实话：**有波动，不完美，但够用。**

- 同一个输入问同一个 Judge 两次，分数可能差 1-2 分（所有 LLM-as-Judge 方案的固有特性）
- **趋势比绝对值重要**：score 从 85 降到 80 比 score 一直是 75 更有参考价值
- temperature 必须设为 0，否则波动更大
- 建议阈值设在 6/10 或 70%，而不是 90%

Judge API key 不配置时会走 mock 逻辑，仅靠关键词命中率打分，**完全不可靠**。开发环境用用可以，CI 中必须配真实 Judge。

详见 [LLM Judge 配置](evaluation/llm-judge.md)。

## Q: 能在生产环境用吗？

**可以，但有条件：**
- 必须修改默认 API key
- 不建议用容器 PostgreSQL（用 Supabase / RDS 托管）
- 需要一个反代（Nginx / Caddy）做 TLS 和限流
- Mock LLM 不能用于生产

当前不支持：多租户、数据自动清理、RBAC。这些功能有计划但还没做。

## Q: Trace 数据会保存多久？

永久 —— 当前版本不自动清理。30 天前的旧数据建议定期删除：

```sql
DELETE FROM traces WHERE created_at < NOW() - INTERVAL '30 days';
```

存储估算：日均 10K traces × ~500 字节/条 ≈ 每月 150MB。

## Q: 怎么贡献代码？

看项目根目录的 `CONTRIBUTING.md`（中英双语）。流程：
1. Fork + 开分支
2. 写代码 + 测试
3. 提 PR
4. GitHub Actions 会自动运行评测，score < 80% 的 PR 会被拦截

大的改动先开 Issue 讨论，不要直接甩大 PR。

## Q: 为什么不用 Go/Rust？

详见 [ADR-001: 为什么用 Python](architecture/adr/001-why-python-backend.md)。

一句话：LLM 生态全在 Python。评测场景是 I/O 密集型（调 LLM API），不是 CPU 密集型，Python async 完全够用。用 Go/Rust 获得的那点性能提升，抵不上失去的生态丰富度。

## Q: 支持非 OpenAI 格式的模型吗？

代理模式只支持 OpenAI 兼容格式。如果你用其他格式的模型：
- 用 SDK 直写 `POST /v1/traces`，自己构造 `user_input` 和 `model_output`
- 或者在 `app/services/trace_collector.py` 的 `proxy_llm_call()` 里改适配逻辑

## Q: 评测一次要多少钱？

分两部分：
1. **被评测模型调用**：取决于模型。用 Mock LLM 免费，用 GPT-4o 约 $0.005/次
2. **Judge 调用**：DeepSeek 约 $0.14/百万 token，可忽略

30 个 case + DeepSeek Judge ≈ $0.01-0.02。100 个 case ≈ $0.05-0.10。

## Q: 怎么处理敏感数据？

当前没有内置脱敏。以下措施可以缓解：
- **自托管**：数据留在你自己的服务器
- **本地 Judge**：用 Ollama 跑本地模型做 Judge，数据不出内网
- **DB 加密**：PostgreSQL 的 TDE 或列级加密

如果你处理的业务含身份证号、手机号等，需要在 SDK 或代理层自行脱敏后再发送。这个功能在 roadmap 上但不是当前优先。
