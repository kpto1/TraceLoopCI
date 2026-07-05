# Changelog

## [0.1.0] - 2026-07-01

### 新增

- Trace 采集代理，支持流式/非流式 OpenAI 兼容接口
- Golden Dataset 构建器，支持从 Trace 一键生成测试用例
- 评测引擎：关键词断言、JSON Schema 校验、LLM-as-Judge
- Next.js Dashboard：Trace 列表 + 详情页
- GitHub Action PR 质量门禁
- Python SDK (pytest plugin) + TypeScript SDK
- Docker Compose 一键部署

### 已知限制

- 仅支持 OpenAI 兼容格式
- LLM-as-Judge 依赖外部裁判模型 API Key
- Redis Streams 消费者为单 worker
