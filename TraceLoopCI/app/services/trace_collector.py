import time
import json
import uuid
import logging
from typing import Optional

import httpx

from app.config import MOCK_LLM_URL

logger = logging.getLogger("traceloop.collector")

# We use a module-level client for connection reuse
_client: Optional[httpx.AsyncClient] = None


async def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
    return _client


async def close_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None


async def proxy_llm_call(
    target_url: str,
    headers: dict,
    body: dict,
    stream: bool = False,
) -> dict:
    """Proxy a request to a real LLM API endpoint and record the trace.

    Returns a dict with the trace data + the raw response (for the caller).
    """
    trace_id = uuid.uuid4().hex[:24]
    t_start = time.monotonic()

    # Extract metadata from the request
    model = body.get("model", "unknown")
    messages = body.get("messages", [])
    system_prompt = None
    user_input = ""
    for m in messages:
        if m.get("role") == "system":
            system_prompt = m.get("content", "")
        elif m.get("role") == "user":
            user_input = m.get("content", "")

    # Prepare forwarding headers (strip host, keep auth)
    fwd_headers = {
        k: v for k, v in headers.items()
        if k.lower() not in ("host", "content-length", "transfer-encoding")
    }

    client = await get_client()
    trace_data = {
        "trace_id": trace_id,
        "user_input": user_input,
        "system_prompt": system_prompt,
        "model": model,
        "temperature": body.get("temperature"),
        "max_tokens": body.get("max_tokens"),
        "status": "success",
    }

    try:
        if stream:
            result = await _proxy_stream(client, target_url, fwd_headers, body, trace_data, t_start)
        else:
            result = await _proxy_non_stream(client, target_url, fwd_headers, body, trace_data, t_start)
        return result
    except httpx.TimeoutException:
        elapsed = (time.monotonic() - t_start) * 1000
        trace_data["status"] = "error"
        trace_data["error_message"] = "Upstream LLM timeout"
        trace_data["latency_ms"] = int(elapsed)
        logger.warning("Trace %s: upstream timeout after %.0fms", trace_id, elapsed)
        return {"trace": trace_data, "response": None, "error": "timeout"}
    except Exception as e:
        elapsed = (time.monotonic() - t_start) * 1000
        trace_data["status"] = "error"
        trace_data["error_message"] = str(e)[:500]
        trace_data["latency_ms"] = int(elapsed)
        logger.warning("Trace %s: error — %s", trace_id, e)
        return {"trace": trace_data, "response": None, "error": str(e)}


async def _proxy_non_stream(client, url, headers, body, trace_data, t_start):
    response = await client.post(url, json=body, headers=headers)
    elapsed = (time.monotonic() - t_start) * 1000
    resp_json = response.json() if response.status_code == 200 else None

    if resp_json and "choices" in resp_json:
        output = resp_json["choices"][0].get("message", {}).get("content", "")
        usage = resp_json.get("usage", {})
        trace_data.update({
            "model_output": output,
            "tokens_prompt": usage.get("prompt_tokens", 0),
            "tokens_completion": usage.get("completion_tokens", 0),
            "tokens_total": usage.get("total_tokens", 0),
            "latency_ms": int(elapsed),
        })
    else:
        trace_data["status"] = "error"
        trace_data["error_message"] = f"Upstream returned {response.status_code}"
        trace_data["latency_ms"] = int(elapsed)

    return {
        "trace": trace_data,
        "response": resp_json,
        "status_code": response.status_code,
    }


async def _proxy_stream(client, url, headers, body, trace_data, t_start):
    first_token_time = None
    full_output = []
    final_usage = {}
    status_code = 200

    async with client.stream("POST", url, json=body, headers=headers) as resp:
        status_code = resp.status_code
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if choices and choices[0].get("delta", {}).get("content"):
                        if first_token_time is None:
                            first_token_time = time.monotonic()
                        full_output.append(choices[0]["delta"]["content"])
                    if "usage" in chunk:
                        final_usage = chunk["usage"]
                except json.JSONDecodeError:
                    continue

    t_end = time.monotonic()
    total_ms = (t_end - t_start) * 1000
    ttft_ms = (first_token_time - t_start) * 1000 if first_token_time else None
    output_text = "".join(full_output)

    if status_code == 200:
        trace_data.update({
            "model_output": output_text,
            "tokens_prompt": final_usage.get("prompt_tokens", 0),
            "tokens_completion": final_usage.get("completion_tokens", 0),
            "tokens_total": final_usage.get("total_tokens", 0),
            "latency_ms": int(total_ms),
            "ttft_ms": int(ttft_ms) if ttft_ms else None,
        })
    else:
        trace_data["status"] = "error"
        trace_data["error_message"] = f"Stream returned {status_code}"
        trace_data["latency_ms"] = int(total_ms)

    return {
        "trace": trace_data,
        "stream_output": output_text,
        "status_code": status_code,
    }
