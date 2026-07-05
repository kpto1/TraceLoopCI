# TraceLoop CI — Python SDK

pytest plugin for LLM behavioral regression testing.

## Install

```bash
pip install trace-loop-ci
```

## Usage

```python
import pytest

@pytest.mark.asyncio
async def test_llm_response(trace_loop):
    # Your LLM call here
    output = "7天内可以退款"

    # Record it
    await trace_loop.record(
        input_text="退款政策是什么？",
        model_output=output,
        model="deepseek-chat",
    )
```

Run with:

```bash
pytest --traceloop-url http://localhost:8000 --traceloop-key your-key
```

The trace will appear in your TraceLoop CI Dashboard.
