# 贡献指南

感谢你考虑为 TraceLoop CI 贡献代码！请花几分钟阅读本指南，让协作更高效。

---

## 报告 Bug

1. 先搜索 [Issues](https://github.com/traceloop-ci/traceloop-ci/issues)，确认是否已有人报告过。
2. 如未找到，请使用 **Bug Report 模板**创建 Issue，内容包括：
   - 做了什么 / 期望什么 / 实际发生了什么
   - 完整复现步骤和环境信息
   - 日志、截图或错误堆栈

## 提交功能建议

使用 **Feature Request 模板**提交，说明：
- 你想解决什么场景下的问题
- 你设想的解决方案（越具体越好）
- 考虑过的替代方案
- 补充信息（参考链接、示例等）

---

## 本地开发环境

### 前置要求

- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Node.js 18+（可选，仅前端开发需要）
- Docker & Docker Compose（可选，推荐）

### 快速启动

```bash
# 1. 克隆仓库
git clone https://github.com/traceloop-ci/traceloop-ci.git
cd traceloop-ci

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate   # Linux/macOS
# venv\Scripts\activate    # Windows

# 3. 安装依赖（含开发依赖）
pip install -e ".[dev]"

# 4. 复制环境变量文件
cp .env.example .env

# 5. 启动依赖服务（Docker Compose）
docker compose up -d postgres redis

# 6. 运行数据库迁移
alembic upgrade head

# 7. 启动服务
uvicorn app.main:app --reload
```

### 使用 Docker Compose 一键启动

```bash
docker compose up -d --build
```

### 前端启动

```bash
cd frontend
pnpm install
pnpm dev
```

---

## 代码风格

- **格式化**：使用 [Black](https://black.readthedocs.io/)，行宽 100
- **Lint**：使用 [Ruff](https://docs.astral.sh/ruff/)，规则集 `E,F,I,N,W,UP`
- **类型检查**：使用 [Mypy](https://mypy.readthedocs.io/)

本地提交前请确保以下命令通过：

```bash
black --check --line-length=100 .
ruff check .
mypy --ignore-missing-imports app/
```

推荐安装 pre-commit 钩子自动检查：

```bash
pip install pre-commit
pre-commit install
```

---

## PR 流程

1. Fork 本仓库，从 `main` 分支创建功能分支
2. 分支命名建议：`fix/xxx`、`feat/xxx`、`docs/xxx`
3. 提交代码，确保测试通过
4. 创建 Pull Request，使用 **PR 模板**填写
5. 等待 Review 和 CI 通过
6. 合并后分支会被删除

### PR 要求

- 新功能必须有对应的测试用例
- 所有测试必须通过
- 代码格式化、Lint 检查必须通过
- 涉及用户体验的改动请更新文档

---

## 测试

```bash
# 运行全部测试
pytest -v

# 带覆盖率
pytest --cov=app --cov-report=term-missing

# 仅运行单元测试
pytest tests/ -m "not integration"

# 运行集成测试（需要 PostgreSQL 和 Redis）
pytest tests/test_integration.py -v
```

---

## 协议

贡献的代码将以 MIT 协议发布。
