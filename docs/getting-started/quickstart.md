# 快速开始

执行根 README 的 `docker compose up -d --build --wait`，打开 http://localhost:3000 。API /docs 位于 8000。前端服务端凭证与 API_KEY 保持一致。默认 Key 仅适合本机演示。

首先通过 `/proxy/v1/chat/completions` 发送带 X-API-Key 的文本请求，然后在 Trace 页面查看。stream=true 返回 SSE，客户端需消费 data 事件。Compose 不自动插入测试数据。
