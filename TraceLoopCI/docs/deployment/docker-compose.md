# Docker Compose 部署

本地开发或单机部署指南。

## 前提

- Docker Desktop 或 Docker Engine 24+
- 至少 2GB 可用内存

## 服务说明

`docker-compose.yml` 定义 4 个服务：

### postgres

- 镜像：`pgvector/pgvector:pg16`
- 端口：5432
- 作用：主数据库，存储 traces、golden cases、评测结果
- pgvector 扩展支持向量检索（预留，当前未使用）
- 数据卷：`pgdata`（持久化到 Docker volume）

### redis

- 镜像：`redis:7-alpine`
- 端口：6379
- 作用：异步 trace 写入的消息队列
- 使用 Redis Streams + 消费者组模式
- 无持久化配置（重启丢队列数据，但 DB 中已有数据不受影响）

### api

- Dockerfile：项目根目录 `Dockerfile`
- 端口：8000
- 命令：`uvicorn app.main:app --host 0.0.0.0 --reload`
- 依赖：等待 postgres 和 redis 健康检查通过
- 代码热重载：开发模式挂载 `./app:/app/app:ro`

### mock-llm

- 同一份 Dockerfile
- 端口：9876
- 命令：`uvicorn app.services.mock_llm:app --host 0.0.0.0`
- 作用：开发时模拟 LLM 响应，避免真实调用消耗或依赖 API key
- 内置关键词触发机制（"退款"、"会员"、"危险"等）

## 环境变量

关键环境变量（开发环境默认值）：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://traceloop:traceloop_dev@postgres:5432/traceloop` | 数据库连接 |
| `REDIS_URL` | `redis://redis:6379/0` | Redis 连接 |
| `MOCK_LLM_URL` | `http://mock-llm:9876` | Mock LLM 地址 |
| `API_KEY` | `dev-api-key-change-in-production` | API 认证密钥 |
| `JUDGE_API_KEY` | `""` | LLM Judge 的 API key（空则使用 mock 评分） |
| `JUDGE_MODEL` | `deepseek-chat` | 评分模型 |
| `JUDGE_BASE_URL` | `https://api.deepseek.com` | 评分模型 API 地址 |

**生产环境务必修改 `API_KEY` 和 `DATABASE_URL`。**

修改方式：复制 `.env.example` 为 `.env`，docker compose 会自动读取：

```bash
cp .env.example .env
# 编辑 .env 修改配置
```

## 数据持久化

PostgreSQL 数据存储在 Docker volume `pgdata` 中：

```bash
# 查看 volume
docker volume inspect traceloopci_pgdata

# 备份
docker exec -t traceloopci-postgres pg_dump -U traceloop traceloop > backup.sql
```

## 代理模式

api 服务提供了 `/proxy/v1/chat/completions` 端点。在开发环境下代理指向 Mock LLM。如果想转发到真实模型，修改环境变量：

```env
MOCK_LLM_URL=https://api.deepseek.com
```

然后发送 OpenAI 兼容的请求体，系统会自动记录 trace。

## 启动和停止

```bash
# 启动所有服务
docker compose up -d

# 查看日志
docker compose logs -f

# 只启动数据库
docker compose up postgres redis -d
docker compose up api -d

# 停止
docker compose down

# 停止并清除数据
docker compose down -v
```

## 健康检查

```bash
# API 服务
curl http://localhost:8000/health

# 代理健康检查
curl -H "X-API-Key: dev-api-key-change-in-production" \
  http://localhost:8000/proxy/health

# Mock LLM
curl http://localhost:9876/health
```

## 已知问题

- `--reload` 模式下文件改动会重启 uvicorn，第一次启动较慢
- Mock LLM 的流式响应每个 chunk 间隔 50ms，不要用于延迟测试
- 同一台机器跑多个项目时注意端口冲突（8000、3000、5432、6379、9876）
