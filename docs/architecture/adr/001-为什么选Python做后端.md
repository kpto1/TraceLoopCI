# ADR 001: 为什么选 Python 做后端

**日期**: 2026-06-28  
**状态**: 已采纳

## 背景

TraceLoop CI 需要选择一个后端语言。核心需求：对接 LLM API（OpenAI/DeepSeek/Qwen 等）、处理 HTTP 代理层、异步写入数据库、跑评测逻辑。需要快速出 MVP，生态支持优先于极致性能。

## 选项

| 选项 | 优点 | 缺点 |
|------|------|------|
| Python (FastAPI) | LLM SDK 全在 Python；FastAPI 异步性能好；AI 开发者最熟悉 | GIL 限制并发；动态类型不如静态类型安全 |
| Go | 并发性能强；编译单二进制部署简单 | LLM 生态弱；团队多数人不熟；开发速度慢 |
| Node.js (Express) | 前端同语言；npm 包多 | 异步模型不适合 CPU 密集型评测；LLM SDK 不如 Python 成熟 |

## 决策

**Python 3.12 + FastAPI**

## 理由

1. LLM 生态全部在 Python。openai、langchain、ragas、instructor — 这些库都是 Python 优先。用别的语言等于自己造轮子。
2. FastAPI 的异步性能对 MVP 够用。单机万级日调用量完全不是瓶颈。
3. 目标用户 — 做 LLM 应用的开发者 — 绝大多数用 Python。他们更容易看懂代码、提 PR。
4. 开发速度快。Python 的动态类型 + FastAPI 的自动文档生成，MVP 迭代效率最高。

## 权衡

- GIL 问题：CPU 密集型评测可通过多 worker（gunicorn/uvicorn workers）缓解。如果后续量级暴涨，可以把评测引擎独立成服务。
- 类型安全：用 mypy + pydantic 做编译期类型校验，部分弥补动态类型的缺陷。
- 性能上限低于 Go/Rust：但以当前万级日调用量的目标，Python 完全够用。过早优化不是好事。
