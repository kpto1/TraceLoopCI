import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import DATABASE_URL
from app.database import Base
from app.models import golden, trace  # noqa: F401


def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def run():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as connection:
        await connection.run_sync(migrate)
    await engine.dispose()


asyncio.run(run())
