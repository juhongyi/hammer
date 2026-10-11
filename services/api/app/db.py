from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Column
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import Field, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from .settings import Settings


def now() -> str:
    return datetime.now(UTC).isoformat()


class CatalogueRow(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    version: int = 1
    document: dict = Field(sa_column=Column(JSON, nullable=False))


class PresentationRow(SQLModel, table=True):
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    source: str
    outline: dict = Field(sa_column=Column(JSON, nullable=False))
    page_count: int
    status: str = "outline_ready"
    phase: str = "개요를 수정하고 확정해 주세요."
    error: str | None = None
    run_id: str | None = None
    snapshot: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    slides: list = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    created_at: str = Field(default_factory=now)


def make_engine(settings: Settings):
    return create_async_engine(settings.database_url, pool_pre_ping=True)


def session_for(engine) -> AsyncSession:
    return AsyncSession(engine, expire_on_commit=False)
