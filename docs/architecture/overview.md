# 架构总览

## 系统架构

```
                     ┌──────────────────────────┐
                     │    SDK / curl / 你的应用    │
                     └────────┬─────────────────┘
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼             │
        ┌────────────┐ ┌──────────┐        │
        │ POST /v1/  │ │ POST /   │        │
        │ traces     │ │ proxy/   │        │
        │ (同步/异步)  │ │ chat/    │        │
        └─────┬──────┘ │ completions│       │
              │        └─────┬─────┘       │
              │              │             │
              ▼              ▼             │
        ┌──────────┐  ┌──────────┐        │
        │ Postgres │  │  Redis   │◄───────┘
        │  (同步)   │  │  Stream  │ (异步写入)
        └────┬─────┘  └────┬─────┘
             │             │
             └──────┬──────┘
                    ▼
           ┌────────────────┐
           │ Redis Consumer │ (trace_writer.py)
           │ 批量写入 (100条) │
           └───────┬────────┘
                   │
                   ▼
           ┌────────────────┐
           │   PostgreSQL   │
           │  pgvector 16   │
           └───┬────┬───────┘
               │    │
         ┌─────▼┐ ┌─▼──────────┐
         │ FastAPI 查询         │
         │ (GET /v1/traces ...) │
         └──────────┬───────────┘
                    │
                    ▼
           ┌────────────────┐
           │  Next.js 16    │
           │   Dashboard    │
           └────────────────┘

  ─── 评测流程 ───

  POST /v1/eval/run
       │
       ▼
  ┌──────────────────┐
  │  eval_runner.py  │
  │  加载 golden cases│
  │  调用 LLM 逐个评测 │
  │  运行 3 个评测器   │
  └───────┬──────────┘
          │
          ▼
  ┌──────────────────┐
  │ 保存 EvalRun 记录 │
  │  到 PostgreSQL   │
  └──────────────────┘
```

## 组件说明

### Trace Collector（trace_collector.py）

接收应用发来的 trace 数据，支持两种模式：
- **代理模式**：拦截 `POST /proxy/v1/chat/completions`，转发到真实 LLM，自动提取请求/响应、token 用量、延迟、TTFT
- **直写模式**：通过 `POST /v1/traces` 或 `/v1/traces/async` 直接写入 trace 数据

代理模式自动处理流式（SSE）和非流式请求。流式模式下会逐块拼装完整输出。

### Redis Streams（trace_writer.py）

写入口 `enqueue_trace()` 是轻量级的 —— 只 push 到 Redis 就返回。后台 `run_consumer()` 从消费者组拉取消息，攒够 100 条或等 1 秒后批量写入 PostgreSQL。

设计决策详见 [ADR-003 Redis Streams not Kafka](../architecture/adr/003-redis-streams-not-kafka.md)。

### PostgreSQL（pgvector 16）

主数据库，存所有业务数据。包含：
- **traces**：LLM 调用日志（含 spans）
- **golden_datasets + golden_cases**：评测数据集
- **eval_runs**：评测执行记录

SQLAlchemy 2.0 async session。连接池 20，overflow 10。

### Eval Engine（eval_runner.py）

评测触发后：
1. 从指定 dataset 加载所有 golden cases
2. 对每个 case，调用目标 LLM 获取回复
3. 遍历所有已注册的评测器（keyword / json_schema / llm_judge）
4. 汇总结果：pass/fail、overall_score、P95 延迟、总成本
5. 保存 EvalRun 记录到数据库

### Dashboard（Next.js 16）

前端只实现最基本功能：查看 traces 列表和详情。其他功能通过 REST API 操作。当前版本前端不展示评测结果。

## 数据流

```
应用 → SDK → POST /v1/traces  → Redis Stream → PostgreSQL
应用 → HTTP → POST /proxy/... → Mock/Real LLM → Redis Stream → PostgreSQL
                                           ↘ 返回响应给应用
Dashboard → GET /v1/traces → PostgreSQL → 展示
用户 → POST /v1/eval/run → Eval Engine → PostgreSQL
```

## 关键设计决策

1. **异步写入是可选而不是默认**。`POST /v1/traces` 直接写 DB（同步），`/v1/traces/async` 走 Redis（异步）。同步写入延迟 ~10ms（取决于网络），但在高并发下 DB 压力大时才需要用 async。
2. **评测不依赖 dashboard**。所有评测操作通过 API，dashboard 只负责查看。
3. **Mock LLM 是内置的**。`app/services/mock_llm.py` 是一个完整的 FastAPI 子应用，独立运行在 9876 端口。不依赖任何外部 API。
4. **评测器和 golden case 紧耦合**。`GoldenCase` 模型的字段直接决定了评测器能做什么（keywords、json_schema、citations）。

## 局限

- 当前只有一个 Redis consumer 进程，批量写入是单线程的。
- 不支持 trace 删除/更新（只有创建和查询）。
- LLM Judge 评测器在 Judge API 不可用时走 mock 逻辑，结果不可靠。
- 没有用户认证系统 —— 只有单个 API key。
