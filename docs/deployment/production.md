# 运维与升级

这是单可信工作区服务。API Key 持有者拥有整个工作区的访问权限，project_id 不提供隔离。Dashboard 必须保持本机访问，或放在带身份认证、TLS、限流的反向代理后；不能把无登录 Dashboard 直接暴露公网。

## 升级

1. 备份 PostgreSQL 并验证能恢复。不要执行 `docker compose down -v`，该命令会删除数据卷。
2. 更新代码与镜像。API 启动前自动执行 `alembic upgrade head`；原始数据库的表会被迁移 0001 接管，0002 添加可空 messages/system_prompt 字段。
3. 检查 `/ready`；`/health` 仅表示进程存活。回滚应用前核实 schema 兼容性；迁移禁用破坏性 downgrade。
4. 首次升级建议停写后执行一次迁移。多副本部署应将迁移拆为一次性 job，避免并发迁移。

## 队列

Redis 使用 AOF 与持久化卷。API 生命周期启动消费者。消息落库后 ACK 并删除；失败消息停留 pending，10 秒闲置后重领。幂等约束为 trace_id。无法解析/验证的消息原样保留在 `traceloop:traces:dead`，需要人工检查；不要盲目删除。不要独立添加同名消费组来归档同一 stream，因为确认后删除是单消费组设计。

这是 at-least-once 策略，不承诺在磁盘故障、Redis 数据丢失或所有持久化目标不可用时零数据损失。监控 backlog、dead stream、Redis 磁盘和数据库容量。

## 数据与凭证

Trace、消息、Span、用例、报告可能包含业务敏感信息。写入前在业务应用做脱敏，仅采集授权数据；限制网络、Key 分发、备份访问。DEBUG 默认关闭；API 不返回内部数据库异常。没有内置 RBAC 或多租户。

定期评估保留策略。以下命令默认只预览，添加 `--apply` 才删除过期 Trace/Span；不会删除用例或报告：

```bash
python -m app.retention --days 30
python -m app.retention --days 30 --apply
```

评测报告、黄金用例和 dead stream 需要单独的保留与审批策略。不要把 `.env`、数据库文件或报告上传公共仓库。

## 发布边界

GitHub required status checks 由仓库管理员配置。真实裁判/模型密钥由部署环境管理，不能把有写权限的密钥注入不可信 PR。默认 PR 示例工作流不使用任何模型密钥，明确标记 heuristic demo。正式业务回归建议在隔离 runner、受限模型代理和经审批的代码上运行。
