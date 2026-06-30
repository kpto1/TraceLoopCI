async def evaluate(golden_case: dict, model_output: str) -> dict:
    """Check that all expected keywords appear and no forbidden keywords appear."""
    expected = golden_case.get("expected_keywords", []) or []
    forbidden = golden_case.get("forbidden_keywords", []) or []

    found_expected = [kw for kw in expected if kw in model_output]
    found_forbidden = [kw for kw in forbidden if kw in model_output]

    missing = [kw for kw in expected if kw not in model_output]
    passed = len(missing) == 0 and len(found_forbidden) == 0

    return {
        "eval_type": "keyword_assertion",
        "passed": passed,
        "score": 1.0 if passed else 0.0,
        "details": {
            "found_keywords": found_expected,
            "missing_keywords": missing,
            "found_forbidden": found_forbidden,
        },
    }
