"""
Import golden test cases into a TraceLoop CI dataset.

This script reads the customer-service-30.json file and imports every
case into a TraceLoop CI dataset via the REST API. Each case becomes a
golden test that the platform uses to detect behavioral regressions in
LLM responses.

Usage:
    python import.py

Requires:
    - TraceLoop CI server at http://localhost:8000
    - Dataset ID (defaults to "customer-service-30", change below)
"""

import json
import sys
import os
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install it with:  pip install httpx")
    sys.exit(1)

# -------------------------------------------------------------------
# Configuration — update these to match your environment
# -------------------------------------------------------------------
TRACELOOP_URL = os.environ.get("TRACELOOP_URL", "http://localhost:8000")
API_KEY = os.environ.get("TRACELOOP_API_KEY", "tl_dev_example_key")
DATASET_ID = os.environ.get("TRACELOOP_DATASET", "customer-service-30")
CASES_FILE = Path(__file__).parent / "customer-service-30.json"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


# -------------------------------------------------------------------
# API helpers
# -------------------------------------------------------------------
def ensure_dataset(client: httpx.Client) -> bool:
    """
    Create the dataset on the server if it doesn't exist yet.

    Returns True if the dataset is ready, False on failure.
    """
    # Check if dataset already exists
    try:
        resp = client.get(
            f"{TRACELOOP_URL}/v1/datasets/{DATASET_ID}",
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            print(f"  [OK] Dataset '{DATASET_ID}' already exists")
            return True
    except httpx.RequestError:
        pass  # Will fall through to create

    # Create it
    try:
        resp = client.post(
            f"{TRACELOOP_URL}/v1/datasets",
            json={
                "id": DATASET_ID,
                "name": "Customer Service 30 — Chinese golden cases",
                "description": "30 golden test cases covering refunds, "
                               "membership, orders, and compliance scenarios",
                "language": "zh-CN",
                "tags": ["customer-service", "chinese", "golden"],
            },
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code in (200, 201):
            print(f"  [OK] Dataset '{DATASET_ID}' created")
            return True
        else:
            print(f"  [ERROR] Failed to create dataset: {resp.status_code} {resp.text}")
            return False
    except httpx.RequestError as exc:
        print(f"  [ERROR] Cannot reach server at {TRACELOOP_URL}: {exc}")
        return False


def import_case(client: httpx.Client, case: dict) -> bool:
    """
    Import a single test case into the dataset.

    The case payload includes:
      - input_text: the user question (sent to the LLM)
      - expected_keywords: words the LLM response MUST contain
      - forbidden_keywords: words the LLM response MUST NOT contain
      - tags: scenario labels for filtering in the dashboard
    """
    payload = {
        "input_text": case["input_text"],
        "expected_keywords": case["expected_keywords"],
        "forbidden_keywords": case["forbidden_keywords"],
        "tags": case.get("tags", []),
    }

    try:
        resp = client.post(
            f"{TRACELOOP_URL}/v1/datasets/{DATASET_ID}/cases",
            json=payload,
            headers=HEADERS,
            timeout=10,
        )

        if resp.status_code in (200, 201):
            return True
        else:
            print(f"    [FAIL] HTTP {resp.status_code}: {resp.text[:120]}")
            return False

    except httpx.RequestError as exc:
        print(f"    [FAIL] Request error: {exc}")
        return False


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
def main():
    print("=" * 56)
    print("  TraceLoop CI — Golden Case Importer")
    print(f"  Server:    {TRACELOOP_URL}")
    print(f"  Dataset:   {DATASET_ID}")
    print(f"  Cases:     {CASES_FILE}")
    print("=" * 56)

    # 1. Load the cases file
    if not CASES_FILE.exists():
        print(f"\n[ERROR] Cases file not found: {CASES_FILE}")
        print("        Run this script from the golden-cases/ directory.")
        sys.exit(1)

    with open(CASES_FILE, "r", encoding="utf-8") as f:
        try:
            cases = json.load(f)
        except json.JSONDecodeError as e:
            print(f"\n[ERROR] Invalid JSON in {CASES_FILE}: {e}")
            sys.exit(1)

    if not isinstance(cases, list):
        print(f"\n[ERROR] Expected a JSON array, got {type(cases).__name__}")
        sys.exit(1)

    print(f"\n  Loaded {len(cases)} test case(s)\n")

    # 2. Connect to the server
    try:
        with httpx.Client() as client:
            # 2a. Ensure the dataset exists
            if not ensure_dataset(client):
                print("\n[ABORT] Cannot proceed without a dataset.")
                sys.exit(1)

            # 2b. Import each case
            succeeded = 0
            failed = 0

            for i, case in enumerate(cases, start=1):
                case_id = case.get("id", f"case-{i:03d}")
                tags = ",".join(case.get("tags", []))
                short_input = case.get("input_text", "")[:40]

                print(f"  [{i:02d}/{len(cases):02d}] {case_id}  {short_input}...")

                if import_case(client, case):
                    succeeded += 1
                    print(f"         -> Imported  ({tags})")
                else:
                    failed += 1

            # 3. Summary
            print(f"\n  {'=' * 40}")
            print(f"  Results: {succeeded} succeeded, {failed} failed out of {len(cases)}")
            if failed > 0:
                print("  Some cases failed. Check the errors above and try again.")
                sys.exit(1)
            else:
                print("  All cases imported successfully!")

    except httpx.RequestError as exc:
        print(f"\n[ERROR] Failed to connect to {TRACELOOP_URL}")
        print(f"        Is the TraceLoop server running?")
        print(f"        Detail: {exc}")
        sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
