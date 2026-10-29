import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://traceloop:traceloop_dev@localhost:5432/traceloop",
)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
MOCK_LLM_URL = os.getenv("MOCK_LLM_URL", "http://localhost:9876")
API_KEY = os.getenv("API_KEY", "dev-api-key-change-in-production")

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "deepseek-chat")
JUDGE_API_KEY = os.getenv("JUDGE_API_KEY", "")
JUDGE_BASE_URL = os.getenv("JUDGE_BASE_URL", "https://api.deepseek.com")

REDIS_STREAM_NAME = "traceloop:traces"
REDIS_CONSUMER_GROUP = "trace-writers"
REDIS_BATCH_SIZE = 100
REDIS_BATCH_TIMEOUT_MS = 1000

LLM_BASE_URL = os.getenv("LLM_BASE_URL", MOCK_LLM_URL)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
WRITER_ENABLED = os.getenv("WRITER_ENABLED", "true").lower() == "true"
RETENTION_DAYS = int(os.getenv("RETENTION_DAYS", "30"))
MAX_BODY_BYTES = int(os.getenv("MAX_BODY_BYTES", "1048576"))
