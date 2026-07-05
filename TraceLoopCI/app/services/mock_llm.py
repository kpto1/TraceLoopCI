import time
import json
import uuid
import asyncio

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, JSONResponse

app = FastAPI(title="mock-llm", version="0.1.0")

_RESPONSES = {
    "退款": "根据我们的退款政策，购买后7天内可申请无理由退款。退款将在3-5个工作日内原路返回到您的支付账户。需要帮助的话请提供订单号。",
    "会员": "我们会员分三个等级：普通会员（免费）、高级会员（￥29/月）和尊享会员（￥99/月）。高级会员享9折和专属客服，尊享会员享8折、优先处理和专属活动邀请。",
    "危险": "您的消息已记录。我们将按照安全规范处理。请勿发送包含个人敏感信息的内容。",
    "客服": "您好，我是AI客服助手。可以帮您解答退款政策、会员权益、订单查询等问题。请问有什么可以帮您？",
}

_DEFAULT = "这是一个模拟回答。在真实环境中这里会是大模型生成的有针对性的回复。"

_STREAM_CHUNKS = [
    "这是", "一个", "模拟", "的", "流式", "回答", "。\n\n",
    "通过", "Mock", " Server", "，", "你可以", "测试", "SSE",
    "流式", "响应", "处理", "逻辑", "，", "而不", "需要",
    "真正", "调用", "LLM", "API", "。",
]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "mock")
    messages = body.get("messages", [])
    stream = body.get("stream", False)

    user_msg = ""
    for m in messages:
        if m.get("role") == "user":
            user_msg = m.get("content", "")

    text = _pick_response(user_msg)

    if stream:
        return StreamingResponse(
            _stream(model, text),
            media_type="text/event-stream",
        )

    prompt_tokens = max(len(user_msg) // 2, 5)
    completion_tokens = max(len(text) // 2, 5)

    return JSONResponse({
        "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": text},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    })


def _pick_response(user_msg: str) -> str:
    if not user_msg:
        return _DEFAULT
    for kw, resp in _RESPONSES.items():
        if kw in user_msg:
            return resp
    return f"关于「{user_msg[:30]}...」的问题，这是一个模拟回答。"


async def _stream(model: str, text: str):
    chunks = [text[i:i+3] for i in range(0, len(text), 3)] or _STREAM_CHUNKS
    for i, chunk in enumerate(chunks):
        payload = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": chunk},
                "finish_reason": None if i < len(chunks) - 1 else "stop",
            }],
        }
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0.05)

    yield "data: [DONE]\n\n"
