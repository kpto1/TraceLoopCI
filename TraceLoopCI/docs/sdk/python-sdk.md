# Python SDK（pytest 插件）

自动记录 pytest 测试中的 LLM 调用作为 trace。

SDK 源码在 `sdk/python/`，通过 pytest11 入口点自动加载。

## 安装

```bash
pip install trace-loop-ci
```

要求 Python >= 3.10。

## 快速开始

```python
import pytest

async def test_chatbot_response(trace_loop):
    # trace_loop 是 pytest fixture，自动注入
    # 它会记录测试中对 LLM 的调用

    async with trace_loop("test-chatbot", model="deepseek-chat") as recorder:
        # 记录一次 LLM 调用
        response = await your_llm_call("退款政策是什么？")
        recorder.record(
            input="退款政策是什么？",
            output=response,
            tokens=42,
            latency_ms=850
        )
```

## 配置

SDK 通过 pytest CLI 选项配置：

```bash
pytest \
  --traceloop-url=http://localhost:8000 \
  --traceloop-key=dev-api-key-change-in-production \
  --traceloop-project=my-project
```

| 选项 | 环境变量 | 默认值 | 说明 |
|---|---|---|---|
| `--traceloop-url` | `TRACELOOP_URL` | `http://localhost:8000` | TraceLoop API 地址 |
| `--traceloop-key` | `TRACELOOP_KEY` | 无 | API Key |
| `--traceloop-project` | `TRACELOOP_PROJECT` | `"default"` | 项目标识 |

不传 `--traceloop-url` 时，`trace_loop` fixture 会跳过（`pytest.skip()`），不影响已有测试。

## fixture 使用模式

### 模式 1：context manager（推荐）

```python
async def test_with_context(trace_loop):
    async with trace_loop("my-scenario", model="gpt-4") as recorder:
        result = await call_llm("Hello")
        recorder.record(input="Hello", output=result)
```

context manager 退出时会自动 flush trace 到服务器。

### 模式 2：手动记录

```python
async def test_manual(trace_loop):
    recorder = trace_loop("manual-scenario", model="deepseek-chat")
    result1 = await call_llm("问题1")
    recorder.record(input="问题1", output=result1)
    result2 = await call_llm("问题2")
    recorder.record(input="问题2", output=result2)
    await recorder.flush()
```

## 实现细节

SDK 内部使用 `trace_loop/plugin.py`：

1. `pytest_configure()`：创建全局 `TraceRecorder`（httpx.AsyncClient）
2. `trace_loop` fixture：提供 `Recorder` 对象，积累 calls 后统一发送
3. 发送失败不影响测试 —— 只打印错误日志
4. 请求发到 `POST {url}/v1/traces`

## 示例

完整的示例见 `examples/pytest-plugin-demo/`：

```bash
cd examples/pytest-plugin-demo
pip install -r requirements.txt
pytest --traceloop-url=http://localhost:8000 --traceloop-key="dev-api-key-change-in-production"
```

示例包含 7 个测试用例，覆盖客服场景的问候、跟进、长上下文、空输入等。

## 局限

- 仅支持 `async def` 测试函数（`@pytest.mark.asyncio`）。同步函数 fixture 不会生效。
- 需要在测试函数参数字段声明 `trace_loop` 参数才会注入。
- 不会自动拦截 httpx/requests 调用 —— 需要显式调用 `recorder.record()`。
- 任何 recorder 内的发送失败只写日志，不抛异常。测试不会因为 trace 发送失败而红。
