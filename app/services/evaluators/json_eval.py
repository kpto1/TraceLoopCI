import json
import jsonschema


async def evaluate(golden_case: dict, model_output: str) -> dict:
    """Validate that the model output is valid JSON matching an optional schema."""
    schema = golden_case.get("expected_json_schema")

    # Try to parse JSON
    try:
        parsed = json.loads(model_output)
    except json.JSONDecodeError as e:
        return {
            "eval_type": "json_schema",
            "passed": False,
            "score": 0.0,
            "details": {"error": f"Invalid JSON: {e.msg}", "valid_json": False},
        }

    result = {"valid_json": True}

    if schema:
        try:
            jsonschema.validate(parsed, schema)
            result["schema_valid"] = True
        except jsonschema.ValidationError as e:
            return {
                "eval_type": "json_schema",
                "passed": False,
                "score": 0.0,
                "details": {
                    "valid_json": True,
                    "schema_valid": False,
                    "error": e.message,
                    "path": list(e.path),
                },
            }

    return {
        "eval_type": "json_schema",
        "passed": True,
        "score": 1.0,
        "details": result,
    }
