"""Psycopg async connections; no connection is opened during import."""

import os
from contextlib import asynccontextmanager

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool


def database_url() -> URL:
    return URL.create(
        "postgresql+psycopg",
        username=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        host=os.environ["PGHOST"],
        port=int(os.environ.get("PGPORT", "5432")),
        database=os.environ["PGDATABASE"],
    )


@asynccontextmanager
async def transaction():
    engine = create_async_engine(database_url(), poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            async with session.begin():
                yield session
    finally:
        await engine.dispose()
