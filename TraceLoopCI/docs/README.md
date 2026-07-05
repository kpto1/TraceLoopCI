# TraceLoop CI 文档

> 一个 LLM 行为回归测试平台。捕获、记录、评测你的 LLM 每一次输出变化。

## 文档结构

```
docs/
├── README.md                  # 你正在看的这个导航页
├── getting-started/
│   ├── quickstart.md          # 5 分钟快速开始：Docker 启动 + 发一条 trace
│   └── first-eval.md          # 第一个评测：创建数据集 → 运行评测 → 看结果
├── deployment/
│   ├── docker-compose.md      # 本地 / 单机部署（Docker Compose）
│   ├── production.md          # 生产环境注意事项（真实建议，不是花架子）
│   └── k8s.md                 # Kubernetes 部署（基础版）
├── sdk/
│   ├── python-sdk.md          # Python pytest 插件使用
│   └── typescript-sdk.md      # TypeScript SDK 使用
├── evaluation/
│   ├── dimensions.md          # 7 个评测维度详解
│   ├── llm-judge.md           # LLM-as-Judge 评分器配置
│   └── custom-rules.md        # 自定义评测规则接入
├── architecture/
│   ├── overview.md            # 架构总览与数据流
│   └── adr/
│       ├── 001-why-python-backend.md
│       ├── 002-postgresql-pgvector.md
│       ├── 003-redis-streams-not-kafka.md
│       └── 004-no-custom-gateway.md
├── faq.md                     # 常见问题（10 个真实问题）
└── troubleshooting.md         # 常见问题排查
```

## 快速导航

| 你想做什么 | 看这个 |
|---|---|
| 第一次跑起来看看 | [快速开始](getting-started/quickstart.md) |
| 跑一个完整的评测 | [第一个评测](getting-started/first-eval.md) |
| 部署到服务器 | [Docker Compose](deployment/docker-compose.md) |
| 接入 Python 项目 | [Python SDK](sdk/python-sdk.md) |
| 接入 TypeScript 项目 | [TypeScript SDK](sdk/typescript-sdk.md) |
| 了解评测维度 | [评测维度说明](evaluation/dimensions.md) |
| 理解为什么这样设计 | [架构决策记录](architecture/adr/001-why-python-backend.md) |
| 遇到问题了 | [故障排查](troubleshooting.md) |

## 项目结构

```
TraceLoopCI/
├── app/                  # FastAPI 后端
│   ├── routes/           # API 接口（traces / proxy / datasets）
│   ├── models/           # SQLAlchemy 模型
│   └── services/         # 业务逻辑（trace 收集、评测引擎）
├── frontend/             # Next.js 16 仪表盘
├── sdk/
│   ├── python/           # Python pytest 插件 trace-loop-ci
│   └── typescript/       # TypeScript SDK track-loop-ci
├── tests/                # 测试（pytest + httpx）
├── examples/             # 使用示例
└── docker-compose.yml    # 一键启动
```

## 核心 API

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/v1/traces` | 写入 trace（同步） |
| POST | `/v1/traces/async` | 写入 trace（异步，经 Redis） |
| GET | `/v1/traces` | 列出 traces（分页+过滤） |
| GET | `/v1/traces/{id}` | 查看单条 trace 详情 |
| POST | `/proxy/v1/chat/completions` | 代理 LLM 请求并记录 trace |
| POST | `/v1/datasets` | 创建数据集 |
| POST | `/v1/datasets/{id}/cases` | 添加 golden case |
| POST | `/v1/eval/run` | 触发评测 |
| GET | `/v1/eval/runs` | 查看评测历史 |

所有 `/v1/*` 和 `/proxy/*` 接口需要 `X-API-Key` 头（开发环境默认 `dev-api-key-change-in-production`）。
