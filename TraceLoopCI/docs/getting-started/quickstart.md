# 5 分钟快速开始

这篇文章带你从零启动 TraceLoop CI，发一条 trace，在仪表盘上看到它。

## 前提

- Docker Desktop（WSL2 模式）或 Docker Engine
- curl（验证用，没有也能用 Postman）

## 第一步：启动服务

```bash
cd C:\Users\lkp23\Desktop\TraceLoopCI
docker compose up -d
```

这会启动 4 个服务（见 `docker-compose.yml`）：
- **postgres**（pgvector/pg16:5432）— 数据存储
- **redis**（redis:7-alpine:6379）— 异步消息队列
- **api**（localhost:8000）— FastAPI 后端
- **mock-llm**（localhost:9876）— 模拟 LLM，开发用

首次启动需要拉镜像、安装 Python 依赖，api 服务会慢一些。

检查服务是否全部就绪：

```bash
docker compose ps
```

期望输出类似：
```
NAME                   STATUS
traceloopci-postgres   healthy
traceloopci-redis      healthy
traceloopci-api        running
traceloopci-mock-llm   running
```

## 第二步：验证 API

```bash
curl http://localhost:8000/
```

返回：
```json
{"service": "TraceLoop CI", "version": "0.1.0", "status": "running"}
```

```bash
curl http://localhost:8000/health
```

返回 `{"status": "ok"}`。

## 第三步：发一条 trace

```bash
curl -X POST http://localhost:8000/v1/traces \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -d '{
    "user_input": "退款政策是什么？",
    "model_output": "我们的退款政策是 7 天内无条件退款。",
    "model": "deepseek-chat",
    "provider": "deepseek",
    "tokens_total": 42,
    "cost": 0.000021,
    "latency_ms": 850
  }'
```

返回：
```json
{"status": "ok", "trace_id": "a1b2c3d4e5f6..."}
```

## 第四步：打开仪表盘

浏览器访问 http://localhost:3000。

你应该能看到刚发的 trace 显示在 Traces 列表中。点进去可以看到完整的输入输出、token 用量、延迟等信息。

如果看到空列表，稍等几秒刷新一下。首次写入可能需要等数据库表创建完成。

## 验证异步写入（可选）

用 async 端点发一条，trace 会先进 Redis 再写入 PostgreSQL：

```bash
curl -X POST http://localhost:8000/v1/traces/async \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-api-key-change-in-production" \
  -d '{
    "user_input": "会员有什么权益？",
    "model_output": "黄金会员享 8 折优惠。",
    "model": "deepseek-chat"
  }'
```

返回 `{"status": "received", "trace_id": "..."}`，等 Redis consumer 处理（最长 1 秒）后就会出现在仪表盘。

## 下一步

你已经验证 TraceLoop CI 能正常运行了。接下来试试 [运行第一个评测](first-eval.md)，或者用 [代理模式](../deployment/docker-compose.md#代理模式) 自动捕获 LLM 调用。
