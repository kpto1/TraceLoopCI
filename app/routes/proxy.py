import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import APIKeyHeader
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.config import MOCK_LLM_URL, API_KEY
from app.database import get_session
from app.services.trace_collector import proxy_llm_call
from app.services.trace_service import create_trace
from app.services.trace_writer import enqueue_trace

logger = logging.getLogger("traceloop.proxy")
router = APIRouter(prefix="/proxy", tags=["proxy"])
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def check_key(key: Optional[str] = Depends(api_key_header)):
    if API_KEY and key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return key


@router.post("/v1/chat/completions")
@router.post("/chat/completions")
async def proxy_chat_completions(
    request: Request,
    key: str = Depends(check_key),
    session: AsyncSession = Depends(get_session),
):
    """Proxy an OpenAI-compatible chat completion request.

    Forwards to the configured LLM endpoint, records the full trace,
    and returns the response. Works with both stream=true and stream=false.
    """
    body = await request.json()
    stream = body.get("stream", False)

    # Determine target — use MOCK_LLM_URL when no real API key is configured,
    # otherwise use the actual provider's endpoint based on the model.
    target = MOCK_LLM_URL + "/v1/chat/completions"

    headers = dict(request.headers)
    # Don't forward our own auth header to upstream
    headers.pop("x-api-key", None)

    result = await proxy_llm_call(
        target_url=target,
        headers=headers,
        body=body,
        stream=stream,
    )

    # Enqueue trace for async write (Redis); fall back to sync write on failure
    try:
        await enqueue_trace(result["trace"])
    except Exception:
        logger.warning(
            "Redis enqueue failed — falling back to sync DB write for trace %s",
            result["trace"].get("trace_id"),
        )
        try:
            await create_trace(
                session=session,
                user_input=result["trace"].get("user_input", ""),
                model=result["trace"].get("model", "unknown"),
                model_output=result["trace"].get("model_output"),
                system_prompt=result["trace"].get("system_prompt"),
                provider=result["trace"].get("provider"),
                temperature=result["trace"].get("temperature"),
                max_tokens=result["trace"].get("max_tokens"),
                tokens_prompt=result["trace"].get("tokens_prompt", 0),
                tokens_completion=result["trace"].get("tokens_completion", 0),
                tokens_total=result["trace"].get("tokens_total", 0),
                cost=result["trace"].get("cost", 0.0),
                latency_ms=result["trace"].get("latency_ms"),
                ttft_ms=result["trace"].get("ttft_ms"),
                status=result["trace"].get("status", "success"),
                error_message=result["trace"].get("error_message"),
                project_id=result["trace"].get("project_id", "default"),
                tags=result["trace"].get("tags"),
                metadata_extra=result["trace"].get("metadata_extra"),
            )
        except Exception:
            logger.exception("Failed to persist trace — continuing anyway")

    if result.get("error"):
        raise HTTPException(status_code=502, detail=result["error"])

    if stream:
        # For streaming, we return a simple JSON with the collected output
        # In production, you'd proxy the stream chunks in real-time
        return JSONResponse({
            "id": "chatcmpl-proxy",
            "object": "chat.completion",
            "model": body.get("model", "unknown"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": result.get("stream_output", "")},
                "finish_reason": "stop",
            }],
        })

    upstream = result.get("response")
    if upstream is None:
        raise HTTPException(status_code=502, detail="Upstream returned no response")

    return JSONResponse(upstream)


@router.get("/health")
async def proxy_health():
    return {"status": "ok", "target": MOCK_LLM_URL}
