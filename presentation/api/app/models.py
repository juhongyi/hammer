"""Atomic outline documents and append-only generation/audit records."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Column, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Presentation(SQLModel, table=True):
    __tablename__ = "presentation"
    __table_args__ = (
        CheckConstraint("status IN ('editing', 'confirmed', 'completed', 'failed')"),
        CheckConstraint("length(input_text) > 0"),
        CheckConstraint("jsonb_array_length(outline->'pages') BETWEEN 5 AND 29"),
        CheckConstraint("status = 'editing' OR confirmed_at IS NOT NULL"),
        CheckConstraint("(status = 'failed') = (failure IS NOT NULL)"),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    input_text: str
    outline: dict = Field(sa_column=Column(JSONB, nullable=False))
    status: str = "editing"
    confirmed_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )
    failure: str | None = None


class Generation(SQLModel, table=True):
    __tablename__ = "generation"
    __table_args__ = (CheckConstraint("jsonb_array_length(pages) BETWEEN 6 AND 30"),)
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    presentation_id: UUID = Field(foreign_key="presentation.id", index=True)
    design_snapshot: dict = Field(sa_column=Column(JSONB, nullable=False))
    pages: list = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )


class Record(SQLModel, table=True):
    __tablename__ = "record"
    __table_args__ = (
        CheckConstraint("attempt BETWEEN 1 AND 2"),
        CheckConstraint("page_position IS NULL OR page_position BETWEEN 0 AND 29"),
        CheckConstraint(
            "kind IN ('candidates', 'decision', 'semantic_review', 'validation')"
        ),
    )
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    presentation_id: UUID = Field(foreign_key="presentation.id", index=True)
    stage: str
    kind: str
    model_id: str | None = None
    page_position: int | None = None
    attempt: int = 1
    payload: dict = Field(sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
