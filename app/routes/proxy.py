import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app import config
from app.security import check_key
from app.services.stream_proxy import persist, stream_response
from app.services.trace_collector import proxy_llm_call

logger = logging.getLogger("traceloop.proxy")
router = APIRouter(prefix="/proxy", tags=["proxy"])


@router.post("/v1/chat/completions")
@router.post("/chat/completions")
async def proxy_chat_completions(
    request: Request,
    key: str = Depends(check_key),
):
    """Proxy an OpenAI-compatible chat completion request.

    Forwards to the configured LLM endpoint, records the full trace,
    and returns the response. Works with both stream=true and stream=false.
    """
    try:
        body = await request.json()
    except ValueError:
        raise HTTPException(422, "Invalid JSON") from None
    if not isinstance(body, dict) or not isinstance(body.get("messages"), list):
        raise HTTPException(422, "messages must be an array")
    if any(
        not isinstance(m, dict) or not isinstance(m.get("content", ""), str)
        for m in body["messages"]
    ):
        raise HTTPException(422, "Only text messages are supported")
    stream = body.get("stream", False)
    target = config.LLM_BASE_URL.rstrip("/") + "/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    auth = (
        f"Bearer {config.LLM_API_KEY}"
        if config.LLM_API_KEY
        else request.headers.get("authorization")
    )
    if auth:
        headers["Authorization"] = auth
    if stream:
        return await stream_response(target, headers, body)

    result = await proxy_llm_call(
        target_url=target,
        headers=headers,
        body=body,
        stream=stream,
    )

    result["trace"]["metadata_extra"] = {"messages": body["messages"]}
    await persist(result["trace"])
    if (
        result.get("error")
        or result.get("status_code", 200) != 200
        or result["trace"].get("status") == "error"
    ):
        raise HTTPException(502, "Upstream request failed")

    upstream = result.get("response")
    if upstream is None:
        raise HTTPException(status_code=502, detail="Upstream returned no response")

    return JSONResponse(upstream)


@router.get("/health")
async def proxy_health():
    return {"status": "ok"}
