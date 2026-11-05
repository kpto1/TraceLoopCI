"""Import sample cases using the actual authenticated dataset API."""

import json
import os
from pathlib import Path

import httpx


def main():
    url = os.getenv("TRACELOOP_URL", "http://localhost:8000")
    key = os.getenv("TRACELOOP_API_KEY", "dev-api-key-change-in-production")
    name = os.getenv("TRACELOOP_DATASET", "customer-service-30")
    cases = json.loads(
        Path(__file__).with_name("customer-service-30.json").read_text(encoding="utf-8")
    )
    with httpx.Client(base_url=url, headers={"X-API-Key": key}, timeout=30) as client:
        response = client.get("/v1/datasets")
        response.raise_for_status()
        dataset = next((d for d in response.json()["items"] if d["name"] == name), None)
        if dataset is None:
            response = client.post(
                "/v1/datasets",
                json={"name": name, "description": "Chinese customer service examples"},
            )
            response.raise_for_status()
            dataset = response.json()
        dataset_id = dataset["id"]
        response = client.get(f"/v1/datasets/{dataset_id}")
        response.raise_for_status()
        existing = {c["input_text"] for c in response.json()["cases"]}
        added = 0
        for case in cases:
            if case["input_text"] in existing:
                continue
            payload = {k: v for k, v in case.items() if k != "id"}
            response = client.post(f"/v1/datasets/{dataset_id}/cases", json=payload)
            response.raise_for_status()
            added += 1
        print(f"Dataset {dataset_id}: {added} cases imported; existing inputs skipped")


if __name__ == "__main__":
    main()
