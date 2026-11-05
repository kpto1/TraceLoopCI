# pytest plugin demo

From the repository root:

```bash
pip install -e sdk/python
python -m pytest examples/pytest-plugin-demo --traceloop-url=http://localhost:8000 --traceloop-key=dev-api-key-change-in-production
```

Uses the actual async `trace_loop.record` fixture. It records explicitly; it does not intercept provider SDKs. Recording failures emit diagnostics and do not override application assertions.
