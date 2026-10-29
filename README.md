# TraceLoop CI

面向中文 LLM 应用的可自托管评测与回归门禁。当前版本面向**单个可信团队/工作区**；`project_id` 是数据标签，不是租户权限边界。

[![CI](https://github.com/kpto1/TraceLoopCI/actions/workflows/ci.yml/badge.svg)](https://github.com/kpto1/TraceLoopCI/actions/workflows/ci.yml)

## 快速启动

```bash
git clone https://github.com/kpto1/TraceLoopCI.git
cd TraceLoopCI
docker compose up -d --build --wait
```

打开 http://localhost:3000 。API 位于 http://localhost:8000/docs 。Compose 会运行 PostgreSQL、持久化 Redis、Mock LLM、API（内置消费者）和前端，自动执行 Alembic 迁移。首次构建需要下载依赖，耗时取决于网络，不承诺 30 秒完成。

本地演示默认 Key 为 `dev-api-key-change-in-production`。前端通过服务端代理携带 Key，浏览器代码不包含密钥。默认只绑定 127.0.0.1，数据库和 Redis 不暴露宿主机端口。

```bash
curl http://localhost:8000/proxy/v1/chat/completions \
  -H 'X-API-Key: dev-api-key-change-in-production' \
  -H 'Content-Type: application/json' \
  -d '{"model":"mock","messages":[{"role":"user","content":"退款政策是什么？"}]}'
```

进入 Traces 查看记录。在“数据集与评测”创建数据集，添加用例或填写 Trace ID 从历史记录生成用例。执行演示时明确取消“要求真实裁判”；正式门禁保留该选项。没有真实裁判的结果标为 degraded，不可冒充语义评测。

## 两种评测入口

1. **API/界面评测**：调用管理员配置的 `LLM_BASE_URL`，可保存基线并比较同一数据集的运行。`revision` 由调用方填写，仅记录声明的版本，不能证明远端代码版本。
2. **PR 应用评测**：使用 CLI 导入当前 checkout 中的实际应用适配器。适配器接收 case 字典，返回输出字符串，可在内部调用 prompt、RAG、工具或模型。CI 对 base 和候选 checkout 分别运行，报告保存两者 commit 标识。

```bash
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps -e .
python -m app.cli --adapter examples.regression_app:answer --cases examples/regression_cases.json --revision BASE_SHA --allow-mock-judge --output baseline.json
# 修改实际被测应用后，再执行候选版本：
python -m app.cli --adapter examples.regression_app:answer --cases examples/regression_cases.json --revision HEAD_SHA --baseline baseline.json --allow-mock-judge
```

`--allow-mock-judge` 仅供无密钥演示。正式评测移除此参数并配置裁判。仓库 `Application regression` 工作流是可运行的示例，需要将 adapter/cases 替换为实际业务入口和经审核的用例。初次接入时 base 中不存在示例适配器，只跑绝对断言并明确提示没有基线；合并后才比较 base/head。不能将示例客服规则视为用户业务质量证明。

## 门禁语义

- 默认最低通过率 80%，默认允许下降 0 个百分点；任何此前通过、现在失败的用例都会阻断。
- 数据集内容或裁判配置不同，拒绝直接比较，须审核并建立新基线。
- 裁判不可用、适配器失败、输出解析失败属于 evaluation_error。
- 未配置裁判时只有显式演示模式允许 degraded 结果；真实裁判调用失败不会回退放行。
- 引用约束按文档标识的字面出现检查，不验证引用内容的真实性。
- 成本未接入供应商计费，因此报告返回 null，不伪造费用；P95 为最近秩定义。
- GitHub 检查失败只有在仓库规则中设为 required check 才能阻止合并。工作流本身不会修改分支保护。

## 实际支持范围

- 文本 OpenAI Chat Completions 代理，非流式和实时 SSE；采集完整 messages、输出及 token/延迟（供应商提供时）。
- 同步 Trace/Span 写入和异步 Redis 写入；稳定 trace_id、pending 重领、幂等写入、坏消息保留到 dead stream。
- Golden Dataset API、Trace 转用例、关键词/JSON Schema/裁判/引用标识检查。
- Trace 页面、数据集操作、基线选择和原始详细评测报告。
- Python pytest 显式 record fixture、TypeScript recordTrace 和传统方法装饰器。

不支持多模态代理、自动推断工具链、跨租户隔离、自动事实核验或已验证的高吞吐 SLA。没有提供竞品能力排行榜；中文优化效果需用真实基准数据验证。

## 真实模型配置

复制 `.env.example` 为 `.env`，分别配置被测模型和裁判：

- `LLM_BASE_URL`：不含 `/v1` 的 OpenAI 兼容服务根地址。
- `LLM_API_KEY`：被测模型凭证，与 TraceLoop API Key 分开。
- `JUDGE_BASE_URL`、`JUDGE_MODEL`、`JUDGE_API_KEY`：裁判配置。
- `API_KEY`：TraceLoop 工作区 Key。真实部署必须更换开发值。

代理可在未设置服务器 `LLM_API_KEY` 时转发调用者 Authorization；不会转发 Cookie 或 TraceLoop Key。API 评测使用服务器配置的模型凭证。

## 开发与验证

Python 3.12+，Node 22+，pnpm 11.25.0。

```bash
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps -e . -e sdk/python
python -m pytest tests sdk/python/tests
ruff check app tests sdk/python migrations
cd frontend
pnpm install --frozen-lockfile
pnpm build
```

Python 依赖以 pyproject.toml 为声明源，跨平台哈希锁文件用于安装。更新依赖后运行 `uv pip compile pyproject.toml --universal --generate-hashes -o requirements.lock` 和带 `--extra dev` 的对应开发锁更新，再执行 CI。不要只更新 requirements.txt。

详见 [运维与升级](docs/deployment/production.md)、[架构](docs/architecture/overview.md)、[评测](docs/evaluation/dimensions.md)。许可证 MIT。
