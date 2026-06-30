import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import DEBUG
from app.database import init_db, close_db
from app.routes.traces import router as traces_router
from app.routes.proxy import router as proxy_router
from app.routes.datasets import router as datasets_router

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("traceloop")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("TraceLoop CI starting...")
    await init_db()
    yield
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
