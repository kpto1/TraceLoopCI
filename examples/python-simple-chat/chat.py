"""Record simulated application responses with the actual Trace API schema."""

import os

import httpx


def main():
    with httpx.Client(
        base_url=os.getenv("TRACELOOP_URL", "http://localhost:8000"),
        headers={"X-API-Key": os.getenv("TRACELOOP_API_KEY", "dev-api-key-change-in-production")},
        timeout=30,
    ) as client:
        for question in ["Hello", "Explain regression testing", "Show a test example"]:
            response = client.post(
                "/v1/traces",
                json={
                    "user_input": question,
                    "model_output": f"Simulated answer: {question}",
                    "model": "demo",
                    "tags": ["python-demo"],
                },
            )
            response.raise_for_status()
            trace_id = response.json()["trace_id"]
            detail = client.get(f"/v1/traces/{trace_id}")
            detail.raise_for_status()
            assert detail.json()["user_input"] == question
            print(f"Recorded and verified {trace_id}")


if __name__ == "__main__":
    main()
