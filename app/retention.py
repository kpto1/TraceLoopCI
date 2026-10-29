"""Explicit retention command; never deletes golden cases or evaluation reports."""

import argparse
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select

from app.database import async_session, close_db
from app.models.trace import Span, Trace


async def prune(days, apply):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    async with async_session() as session:
        count = await session.scalar(
            select(func.count()).select_from(Trace).where(Trace.created_at < cutoff)
        )
        print(f"{count} traces older than {days} days; apply={apply}")
        if apply:
            ids = select(Trace.id).where(Trace.created_at < cutoff)
            await session.execute(delete(Span).where(Span.trace_id_fk.in_(ids)))
            await session.execute(delete(Trace).where(Trace.created_at < cutoff))
            await session.commit()
    await close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("days must be positive")
    asyncio.run(prune(args.days, args.apply))
