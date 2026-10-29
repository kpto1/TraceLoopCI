# Docker Compose

从仓库根运行 `docker compose up -d --build --wait`。五个服务：postgres、redis、mock-llm、api、frontend。数据库和 Redis 只有内部网络访问，前端与 API 绑定 127.0.0.1。

API 首先运行 Alembic，再启动内置消费者。Redis AOF 数据位于 redisdata，PostgreSQL 位于 pgdata。查看 `docker compose logs api` 定位迁移或消费问题。升级与备份见 production.md。

不要在需要保留数据时使用 down -v。普通 `docker compose down` 保留数据卷。
