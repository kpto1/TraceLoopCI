# TraceLoop CI Examples

This directory contains runnable example projects that demonstrate different
features of TraceLoop CI, an LLM behavioral regression testing platform.

## Examples

### `python-simple-chat/`

A minimal Python chatbot that records LLM call traces through the TraceLoop
proxy. Demonstrates the basic recording flow: intercepting API calls, sending
trace data to the server, and verifying what was captured.

Run with: `python chat.py`

### `pytest-plugin-demo/`

A pytest-based test suite that uses the TraceLoop pytest plugin to record
LLM interactions during testing. Demonstrates how to integrate behavioral
regression testing into your CI pipeline with GitHub Actions.

Run with: `pytest --traceloop-url http://localhost:8000`

### `golden-cases/`

A curated set of 30 golden test cases for Chinese customer service scenarios,
covering refunds, membership benefits, order tracking, and compliance.
Includes an import script that loads the cases into a TraceLoop CI dataset
via the REST API.

Run with: `python import.py`

---

Each example has its own README with detailed instructions. All examples
expect a TraceLoop CI server running at `http://localhost:8000`.
