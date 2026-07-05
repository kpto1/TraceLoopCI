"""
TraceLoop CI — Minimal Python chatbot demo.

This script demonstrates the basic LLM tracing flow:
  1. Configure the TraceLoop client to intercept LLM API calls
  2. Send a chat request (simulated — no real API key needed)
  3. The trace is recorded and sent to the TraceLoop server
  4. Verify the trace was captured

Run:  python chat.py

Requires a TraceLoop CI server running at http://localhost:8000.
"""

import httpx
import time
import uuid

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
TRACELOOP_URL = "http://localhost:8000"
TRACELOOP_API_KEY = "tl_dev_example_key_12345"

# A fake session identifier — in production this comes from the SDK
SESSION_ID = str(uuid.uuid4())[:8]

# -------------------------------------------------------------------
# Step 1: Send a chat message and record the trace
# -------------------------------------------------------------------
def send_chat(user_message: str) -> dict:
    """
    Simulate sending a chat to an LLM and recording the trace.

    In production the TraceLoop SDK intercepts the HTTP call to the LLM
    provider automatically. Here we build the trace payload by hand so
    the demo has zero dependencies beyond httpx.
    """
    trace_payload = {
        "session_id": SESSION_ID,
        "timestamp": time.time(),
        "model": "gpt-4o-mini",
        "provider": "openai",
        "request": {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.7,
            "max_tokens": 512,
        },
        "response": {
            "role": "assistant",
            # Simulated LLM response
            "content": f"I received your message: '{user_message[:50]}'. "
                       f"This is a simulated response for tracing purposes.",
            "finish_reason": "stop",
        },
        "usage": {
            "prompt_tokens": 28,
            "completion_tokens": 15,
            "total_tokens": 43,
        },
    }

    print(f"  Sending trace for: \"{user_message}\"")
    return trace_payload


def record_trace(payload: dict) -> bool:
    """
    POST the trace payload to the TraceLoop CI server.

    The server stores the trace and makes it available for:
      - Reviewing in the dashboard
      - Adding to a golden dataset
      - Running evaluations against future model versions
    """
    headers = {
        "Authorization": f"Bearer {TRACELOOP_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        resp = httpx.post(
            f"{TRACELOOP_URL}/v1/traces",
            json=payload,
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        print(f"  [OK] Trace recorded — ID: {resp.json().get('id', 'unknown')}")
        return True

    except httpx.HTTPStatusError as exc:
        print(f"  [ERROR] Server returned {exc.response.status_code}: {exc.response.text}")
    except httpx.RequestError as exc:
        print(f"  [ERROR] Could not reach TraceLoop server at {TRACELOOP_URL}")
        print(f"          Is the server running? ({exc})")
    except Exception as exc:
        print(f"  [ERROR] Unexpected error: {exc}")

    return False


# -------------------------------------------------------------------
# Step 2: Query recorded traces (optional verification)
# -------------------------------------------------------------------
def list_traces() -> list[dict]:
    """Fetch recent traces from the server to verify recording worked."""
    try:
        resp = httpx.get(
            f"{TRACELOOP_URL}/v1/traces",
            params={"session_id": SESSION_ID, "limit": 10},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("traces", resp.json().get("data", []))
    except Exception:
        return []


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
def main():
    print("=== TraceLoop CI: Python Chat Demo ===\n")
    print(f"Session ID: {SESSION_ID}")
    print(f"Server:     {TRACELOOP_URL}\n")

    # Messages to trace
    messages = [
        "What is the capital of France?",
        "Explain neural networks in simple terms.",
        "Write a haiku about unit testing.",
    ]

    for msg in messages:
        payload = send_chat(msg)
        record_trace(payload)
        print()  # blank line between messages

    # Verify — fetch back the traces we just recorded
    print("--- Verifying recorded traces ---")
    traces = list_traces()
    if traces:
        print(f"  Found {len(traces)} trace(s) for session {SESSION_ID}")
        for t in traces[:3]:
            req_messages = t.get("request", {}).get("messages", [])
            user_msg = next(
                (m["content"] for m in req_messages if m.get("role") == "user"),
                "(no user message)",
            )
            print(f"    - User: {user_msg[:60]}...")
    else:
        print("  No traces found (server may not be running or traces endpoint differs).")
        print("  This is expected if you're just reading the code — the logic is correct.")

    print("\n=== Demo complete ===")
    print("Next steps:")
    print("  1. Start the TraceLoop server on port 8000")
    print("  2. Run `python chat.py` to see traces being recorded")
    print("  3. Check the TraceLoop dashboard to review your traces")


if __name__ == "__main__":
    main()
