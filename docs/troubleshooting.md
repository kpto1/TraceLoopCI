# 故障排查

- 前端 502：确认 API 运行，服务端 TRACELOOP_API_URL 可达。
- API 401：确认 X-API-Key 与 API_KEY 一致；前端使用服务端 TRACELOOP_API_KEY。
- /ready 503：检查 database、redis、writer 三项及 API 日志；/health 不代表依赖健康。
- Trace 不出现：检查 Redis pending、dead stream、消费者日志；UI 默认查询 default 项目。
- Judge 错误：检查独立的 JUDGE_* 配置。禁止以 Mock 降级结果冒充真实通过。
- 基线不兼容：数据集或裁判配置改变，需要重新审核建立基线。
- aiosqlite 缺失：安装 requirements-dev.lock；不要混用旧 requirements 清单。
- Windows 中文：文件与请求使用 UTF-8；避免依赖系统默认编码。
- Docker 不可用：先确认 Docker Desktop 引擎已启动和当前用户有管道访问权限。
