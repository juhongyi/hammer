"""Presentation aggregates and historical generation evidence.

Outline JSON follows schemas.Outline: one cover plus ordered chapters/pages/items.
Keeping each outline as one document makes the confirmed structure atomic. JSON
documents must be validated with schemas before persistence; SQL constraints cover
local integrity, not the entire contract. Confirmed outlines, design snapshots and
finished generations are historical values: future writers must not update them.
There are deliberately no foreign keys into the independently owned ontology DB.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import JsonValue
from sqlalchemy import CheckConstraint, DateTime, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class Presentation(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("length(trim(input_text)) > 0", name="request_not_empty"),
        CheckConstraint("status IN ('editing', 'confirmed')", name="outline_status"),
        CheckConstraint(
            "(status = 'editing' AND confirmed_outline IS NULL) OR "
            "(status = 'confirmed' AND outline IS NOT NULL "
            "AND confirmed_outline IS NOT NULL "
            "AND outline = confirmed_outline)",
            name="confirmed_outline_preserved",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    input_text: str
    status: str = Field(default="editing")
    outline: dict[str, JsonValue] | None = Field(
        default=None, sa_type=JSONB(none_as_null=True)
    )
    confirmed_outline: dict[str, JsonValue] | None = Field(
        default=None, sa_type=JSONB(none_as_null=True)
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True)
    )


class DesignSnapshot(SQLModel, table=True):
    """Complete copy of ontology.schemas.Catalog, independent of live definitions."""

    __tablename__ = "design_snapshot"
    __table_args__ = (
        CheckConstraint("schema_version = 1", name="snapshot_schema_version"),
        CheckConstraint(
            "jsonb_typeof(catalog) = 'object' "
            "AND catalog ?& ARRAY['schema_version', 'expression_types', 'layouts']",
            name="snapshot_catalog_shape",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    schema_version: int = Field(default=1)
    catalog: dict[str, JsonValue] = Field(sa_type=JSONB)
    captured_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True)
    )


class Generation(SQLModel, table=True):
    """A generation attempt inside a request, not a background job/queue entry.

    slides follows schemas.GeneratedSlide; each selected layout/type/slot refers
    to design_snapshot, never to the current ontology. The confirmed outline is
    copied so subsequent product changes cannot reinterpret historical results.
    """

    __table_args__ = (
        UniqueConstraint("presentation_id", "id"),
        CheckConstraint(
            "status IN ('generating', 'completed', 'failed')", name="generation_status"
        ),
        CheckConstraint(
            "(status = 'failed' AND error IS NOT NULL AND length(trim(error)) > 0) "
            "OR (status != 'failed' AND error IS NULL)",
            name="generation_error",
        ),
        CheckConstraint("jsonb_typeof(slides) = 'array'", name="slides_array"),
        CheckConstraint("slide_count BETWEEN 6 AND 30", name="generation_slide_count"),
        CheckConstraint(
            "jsonb_array_length(slides) <= slide_count AND "
            "(status != 'completed' OR jsonb_array_length(slides) = slide_count)",
            name="complete_deck_required",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    presentation_id: UUID = Field(foreign_key="presentation.id", index=True)
    design_snapshot_id: UUID = Field(foreign_key="design_snapshot.id")
    confirmed_outline: dict[str, JsonValue] = Field(sa_type=JSONB)
    slide_count: int
    status: str = Field(default="generating")
    slides: list[dict[str, JsonValue]] = Field(default_factory=list, sa_type=JSONB)
    error: str | None = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True)
    )


class DecisionRecord(SQLModel, table=True):
    """Candidate definitions, selections and review evidence for both attempts."""

    __tablename__ = "decision_record"
    __table_args__ = (
        ForeignKeyConstraint(
            ["presentation_id", "generation_id"],
            ["generation.presentation_id", "generation.id"],
        ),
        CheckConstraint("attempt BETWEEN 1 AND 2", name="decision_attempt"),
        CheckConstraint(
            "stage IN ('slide_count', 'chapter_count', 'chapter_boundaries', "
            "'expression_type', 'layout', 'outline_review', 'text_review', "
            "'structure_review', 'render_review')",
            name="decision_stage",
        ),
        CheckConstraint(
            "verdict IS NULL OR verdict IN ('passed', 'failed', 'error')",
            name="decision_verdict",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    presentation_id: UUID = Field(foreign_key="presentation.id", index=True)
    generation_id: UUID | None = Field(default=None, index=True)
    page_id: UUID | None = None
    stage: str
    attempt: int = Field(default=1)
    provider: str
    model: str
    candidates: list[dict[str, JsonValue]] = Field(default_factory=list, sa_type=JSONB)
    selected_id: str | None = None
    verdict: str | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict, sa_type=JSONB)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC), sa_type=DateTime(timezone=True)
    )
