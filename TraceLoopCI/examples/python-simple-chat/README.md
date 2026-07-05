# TraceLoop CI: Python Simple Chat

A minimal demo showing how to record LLM call traces with TraceLoop CI.

## What it demonstrates

- Constructing a trace payload (request, response, token usage)
- POSTing the trace to the TraceLoop server (`/v1/traces`)
- Verifying recorded traces by fetching them back
- Graceful error handling when the server is unavailable

## Requirements

- Python 3.10+
- A TraceLoop CI server running on `http://localhost:8000`

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python chat.py
```

If the server is not running, the script will still demonstrate the code
paths with clear error messages. Start the server and re-run to see
traces recorded successfully.

## Key concepts

| Concept     | Description                                    |
|-------------|------------------------------------------------|
| Trace       | A single LLM request/response pair             |
| Session     | A group of related traces (e.g. one user chat) |
| Proxy flow  | SDK intercepts LLM calls automatically         |
| Manual flow | Demo builds payloads directly for clarity      |
