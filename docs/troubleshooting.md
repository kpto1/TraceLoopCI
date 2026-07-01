# 故障排查

> 遇到问题先看这里。都是真实遇到过的坑。

## 服务启动失败

### Docker 容器起不来

```bash
# 先看哪些挂了
docker compose ps

# 看具体日志
docker compose logs api | tail -30
docker compose logs postgres | tail -30
```

**常见原因：**

**1. 端口占用**
```bash
# Windows 检查端口
netstat -ano | findstr "5432 6379 8000 3000 9876"

# 有占用就改 docker-compose.yml 的 ports 映射
# 比如把 "5432:5432" 改成 "5433:5432"
```

**2. Docker 资源不足**
- Docker Desktop → Settings → Resources → 调高内存到 4GB+
- WSL2 模式确保有足够 swap

**3. WSL2 问题（Windows）**
```powershell
# PowerShell 管理员
wsl --install
wsl --set-default-version 2
```

### API 启动后连不上数据库

```bash
docker compose logs api | grep -i "error\|connection\|refused"
```

最常见原因：postgres 容器还在初始化，API 先启动了。docker compose 的健康检查（healthcheck）应该等 postgres 就绪，但有时会超时。

**手动解决：**
```bash
docker compose restart api
```

## Trace 没入库

发了 `POST /v1/traces` 返回 `{"status": "ok"}`，但查询不到。

**排查步骤：**

```bash
# 1. 确认 trace 写入了数据库
docker compose exec postgres psql -U traceloop -d traceloop -c "SELECT count(*) FROM traces;"

# 2. 检查异步 consumer 是否在运行（如果是 /v1/traces/async）
docker compose logs api | grep "writer\|consumer\|stream"

# 3. 检查 Redis stream 积压情况
docker compose exec redis redis-cli XLEN traceloop:traces
```

如果 `XLEN` 值持续增长，说明 consumer 没在消费。重启 api：

```bash
docker compose restart api
```

**同步写入（`/v1/traces`）如果也查不到：**
- 确认 `X-API-Key` 正确
- 确认请求体格式正确（特别是 `user_input` 和 `model` 字段）
- 看 API 日志有无 SQLAlchemy 报错

## 评测一直跑不完

评测（`POST /v1/eval/run`）需要为每个 golden case 调用一次 LLM。

```bash
# 1. 确认 Mock LLM（或目标模型）能访问
curl http://localhost:9876/health

# 2. 检查 Mock LLM 日志
docker compose logs mock-llm | tail -20

# 3. 如果是真实模型，检查网络和 API key
```

**30 个 case 跑 5 分钟以上？** 可能原因：
- Mock LLM 没启动，请求超时（默认 120s）
- 网络代理/防火墙阻挡了 LLM API 调用
- Judge API key 没配，但被评测的模型调用了真实 API 超时

**解决：** 如果是 Mock LLM 问题，确认 `MOCK_LLM_URL` 指向正确地址。默认是 `http://mock-llm:9876`。

## 前端连不上后端

前端页面打开后白屏或一直 loading。

```bash
# 打开浏览器开发者工具 -> Console，看具体报错
```

**常见错误：**
```
Access to fetch at 'http://localhost:8000/v1/traces' from origin 'http://localhost:3000' has been blocked by CORS
```

**原因：** 前端（:3000）请求后端（:8000）被 CORS 拦截。

**解决：** 检查 `app/main.py` 中 CORS 配置：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    # ...
)
```

如果不在同一台机器，需要添加前端的实际域名/IP。

## Docker 启动报错 WSL2 / Hyper-V

**症状：** `Docker Desktop requires a newer WSL2 kernel` 或 `Hardware assisted virtualization and data execution protection must be enabled in the BIOS`

**解决：**
```powershell
# 以管理员运行 PowerShell
wsl --update
wsl --set-default-version 2
```

如果 `wsl --update` 失败，手动下载 WSL2 Linux 内核更新包：https://aka.ms/wsl2kernel

BIOS 中需要启用虚拟化（VT-x/AMD-V）。不同主板位置不同，一般叫 "Intel Virtualization Technology" 或 "SVM Mode"。

## 数据库迁移失败

项目使用 SQLAlchemy `create_all` 自动建表，不需要手动迁移。

但如果你改了模型定义，`create_all` **不会更新已有表结构**。

**方案 A（开发环境）：** 删表重建
```bash
docker compose exec postgres psql -U traceloop -d traceloop
# DROP TABLE IF EXISTS traces, spans, golden_datasets, golden_cases, eval_runs CASCADE;
# \q
docker compose restart api
```

**方案 B（生产环境）：** 用 Alembic
```bash
pip install alembic
alembic init alembic
# 修改 alembic.ini 的 sqlalchemy.url
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

## 端口占用一览

| 端口 | 服务 | 改了哪里 |
|---|---|---|
| 3000 | Next.js 前端 | `frontend/next.config.ts` |
| 5432 | PostgreSQL | `docker-compose.yml` + `DATABASE_URL` |
| 6379 | Redis | `docker-compose.yml` + `REDIS_URL` |
| 8000 | FastAPI 后端 | `docker-compose.yml` |
| 9876 | Mock LLM | `docker-compose.yml` + `MOCK_LLM_URL` |

## 诊断脚本

快速检查所有服务状态：

```bash
echo "=== API ==="
curl -s http://localhost:8000/health
echo ""

echo "=== Mock LLM ==="
curl -s http://localhost:9876/health
echo ""

echo "=== DB ==="
docker compose exec postgres pg_isready -U traceloop

echo "=== Redis ==="
docker compose exec redis redis-cli ping

echo "=== Redis Stream Backlog ==="
docker compose exec redis redis-cli XLEN traceloop:traces

echo "=== Trace Count ==="
docker compose exec postgres psql -U traceloop -d traceloop -c "SELECT count(*) FROM traces;"
```

## 还是没解决？

开 GitHub Issue：https://github.com/your-org/traceloop-ci/issues

附上：
- `docker compose logs api | tail -50` 的输出
- 你的 `docker-compose.yml`（去掉敏感信息）
- 完整请求和响应（去掉敏感信息）
