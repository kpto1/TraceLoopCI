# Python pytest 插件

```bash
pip install -e sdk/python
pytest --traceloop-url=http://localhost:8000 --traceloop-key=dev-api-key-change-in-production
```

在异步测试中调用 `await trace_loop.record(input_text, output, model="mock")`。这是显式记录 fixture，不会自动拦截所有模型 SDK。每次记录使用有界超时并关闭 HTTP 客户端；记录失败输出诊断但不更改业务断言结果。
