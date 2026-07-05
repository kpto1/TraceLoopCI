# 生产环境部署注意事项

> 这不是那种"企业级 12 因素"废话文档。真实团队的心得。

## 用托管 PostgreSQL，别自己容器化

docker-compose 里的 PostgreSQL 只适合开发。生产环境用托管服务：

- **Supabase**：免费额度够用，pgvector 内置。10K traces/天完全免费。
- **Railway**：一键部署，自动备份，有 pgvector。
- **AWS RDS / Aurora**：如果你们已经在 AWS 上。

**不推荐**自己维护容器 PostgreSQL 的原因：
- 备份恢复要自己写 cron
- 内存/磁盘监控要自己搞
- 故障恢复也是你的活

## API 密钥

```env
# 开发环境
API_KEY=dev-api-key-change-in-production

# 生产环境 —— 用足够长的随机字符串
API_KEY=$(openssl rand -hex 32)
# 结果类似：a7d8f3c2e1b4a9c6d5e2f1b8a3c4d7e6f9a8b1c2d3e4f5a6b7c8d9e0f1a2b3c4
```

SDK 和 curl 请求都需要传 `X-API-Key` 头。

## 反向代理（Nginx）

如果要在公网暴露 API，用 Nginx 反代 + 可选的流式支持：

```nginx
server {
    listen 443 ssl;
    server_name traceloop.yourcompany.com;

    location / {
        proxy_pass http://127.0.0.1:8000;

        # 流式响应必备
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding on;
        proxy_buffering off;
        proxy_cache off;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

`proxy_buffering off` 和 `chunked_transfer_encoding on` 这两行是关键 —— LLM 流式响应依赖它们。忘记加的话 SSE 会被 Nginx 缓存然后一次性吐出，前端等不到逐 token 效果。

## 备份策略

用托管数据库的话，一般自带自动备份。如果是自建：

```bash
# 每天凌晨 3 点备份，保留 7 天
0 3 * * * pg_dump -U traceloop traceloop | gzip > /backups/traceloop-$(date +\%Y\%m\%d).sql.gz
0 3 * * * find /backups -name "traceloop-*.sql.gz" -mtime +7 -delete
```

备份内容包含 traces、golden datasets、eval runs。Redis 不备份（重启后从 DB 重新消费）。

## 资源估算

| 日 trace 量 | 推荐配置 | 数据库存储 |
|---|---|---|
| < 1K | 1 vCPU, 1GB RAM | ~50MB/月 |
| 10K | 1 vCPU, 2GB RAM | ~500MB/月 |
| 100K | 2 vCPU, 4GB RAM | ~5GB/月 |
| 1M+ | 考虑扩容读写分离 | ~50GB/月 |

以上是保守估计，单条 trace 平均 ~500 字节（含 metadata 和 spans）。

## 监控

最低限度：

```bash
# 资源监控
docker stats traceloopci-api

# 应用日志 —— 重点关注
docker compose logs api | grep -E "ERROR|WARNING"

# API 响应 —— 正常应 < 50ms（不包括 LLM 代理耗时）
curl -o /dev/null -s -w "%{time_total}\n" http://localhost:8000/health
```

建议监控项：
- `GET /health` 返回非 200 -> 告警
- Redis 消费者组积压（`XLEN traceloop:traces` > 1000）-> trace 写入跟不上
- PostgreSQL 连接数（默认 pool 20）-> 接近上限说明需要调整 pool_size

## 不推荐的事情

- **不要**把前端和后端部署在同一端口下。前端是 Next.js 静态站，后端是 FastAPI。分开部署或反代。
- **不要**在生产开 `--reload`。它热重载很香，但会泄露源码路径到错误信息里。
- **不要**在生产用 Mock LLM。那是开发调试用的。
