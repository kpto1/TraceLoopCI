# TraceLoop CI: Pytest Plugin Demo

Shows how to integrate TraceLoop CI into your pytest test suite for
automated LLM behavioral regression testing.

## What it demonstrates

- Configuring the TraceLoop plugin via `conftest.py`
- Using the `trace_loop` fixture to record LLM call traces
- Running tests as a CI quality gate (fail on regression)
- Grouping traces by session and test name

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
pytest --traceloop-url http://localhost:8000 -v
```

To use a specific session ID (e.g. for CI run grouping):

```bash
pytest --traceloop-url http://localhost:8000 \
       --traceloop-session "pr-42-commit-abc123" -v
```

## GitHub Actions integration

```yaml
# .github/workflows/traceloop.yml
- name: Run LLM regression tests
  run: |
    pytest --traceloop-url ${{ secrets.TRACELOOP_URL }} \
           --traceloop-api-key ${{ secrets.TRACELOOP_KEY }} \
           --traceloop-session "pr-${{ github.event.number }}" \
           -v --junitxml=report.xml
```

The test run is linked to the PR so you can see which changes caused
regressions before merging.

## Key concepts

| Concept      | Description                                      |
|--------------|--------------------------------------------------|
| Fixture      | `trace_loop` injects a recording client          |
| Session      | Group traces across multiple test files           |
| CI gate      | PR quality check via GitHub Actions               |
| Flush        | Traces are uploaded after each test completes     |
