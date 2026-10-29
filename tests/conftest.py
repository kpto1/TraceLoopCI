import os

os.environ.setdefault(
    "DATABASE_URL", "sqlite+aiosqlite:///file:traceloop-test?mode=memory&cache=shared&uri=true"
)
os.environ["API_KEY"] = ""
os.environ["DEBUG"] = "false"

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
async def _init_db():
    from app.database import close_db, init_db

    await init_db()
    yield
    await close_db()


@pytest.fixture
async def client():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
