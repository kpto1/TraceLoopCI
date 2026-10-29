import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import config
from app.config import DEBUG
from app.database import async_session, close_db, engine
from app.middleware import BodyLimitMiddleware
from app.routes.datasets import router as datasets_router
from app.routes.proxy import router as proxy_router
from app.routes.traces import router as traces_router
from app.services.trace_collector import close_client
from app.services.trace_writer import HEARTBEAT, _redis, run_consumer

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("traceloop")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TraceLoop CI starting...")
    # Production schemas are managed by `alembic upgrade head` before startup.
    writer = asyncio.create_task(run_consumer(async_session)) if config.WRITER_ENABLED else None
    try:
        yield
    finally:
        if writer:
            writer.cancel()
            with suppress(asyncio.CancelledError):
                await writer
        await close_client()
        await close_db()
    logger.info("TraceLoop CI stopped")


app = FastAPI(
    title="TraceLoop CI",
    version="0.1.0",
    description="LLM behavioral regression testing",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(traces_router)
app.include_router(proxy_router)
app.include_router(datasets_router)


@app.get("/")
def root():
    return {
        "service": "TraceLoop CI",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


app.add_middleware(BodyLimitMiddleware)


@app.exception_handler(ValueError)
async def invalid_value(request: Request, exc: ValueError):
    return JSONResponse({"detail": "Invalid request or incompatible baseline"}, status_code=400)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.exception("Request failed", exc_info=exc)
    return JSONResponse({"detail": "Internal service error"}, status_code=500)


@app.get("/ready")
async def readiness():
    checks = {}
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1 FROM traces LIMIT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False
    r = await _redis()
    try:
        checks["redis"] = bool(await r.ping())
        checks["writer"] = bool(await r.get(HEARTBEAT)) if config.WRITER_ENABLED else False
    except Exception:
        checks.update(redis=False, writer=False)
    finally:
        await r.aclose()
    return JSONResponse(
        {"status": "ready" if all(checks.values()) else "unavailable", "checks": checks},
        status_code=200 if all(checks.values()) else 503,
    )
