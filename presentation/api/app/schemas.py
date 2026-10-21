from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class Health(BaseModel):
    status: Literal["ok"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Content(Contract):
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)


class Page(Contract):
    id: UUID
    title: str = Field(min_length=1)
    key_message: str = Field(min_length=1)
    contents: list[Content] = Field(max_length=6)


class Chapter(Contract):
    id: UUID
    title: str = Field(min_length=1)
    page_ids: list[UUID] = Field(min_length=1)


class Outline(Contract):
    cover_title: str = Field(min_length=1)
    chapters: list[Chapter] = Field(min_length=1)
    pages: list[Page] = Field(min_length=5, max_length=29)

    @model_validator(mode="after")
    def valid_partition(self):
        ids = [page.id for page in self.pages]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate page id")
        if len({c.id for c in self.chapters}) != len(self.chapters):
            raise ValueError("duplicate chapter id")
        if [pid for c in self.chapters for pid in c.page_ids] != ids:
            raise ValueError("chapters must partition body pages in order")
        return self

    def structure(self):
        return ([p.id for p in self.pages], [(c.id, c.page_ids) for c in self.chapters])


class PresentationCreate(Contract):
    input_text: str = Field(min_length=1)
    outline: Outline


class PresentationRead(PresentationCreate):
    id: UUID
    status: Literal["editing", "confirmed", "completed", "failed"]
    confirmed_at: datetime | None
    failure: str | None


class DesignSnapshot(Contract):
    """Versioned OntologyDefinition wire document, copied without transformation."""

    schema_version: Literal[1] = 1
    expression_types: list[dict[str, JsonValue]] = Field(min_length=1)
    layouts: list[dict[str, JsonValue]] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_ids(self):
        for definitions in (self.expression_types, self.layouts):
            ids = [d.get("id") for d in definitions]
            if any(not isinstance(i, str) or not i for i in ids):
                raise ValueError("snapshot definitions require string ids")
            if len(set(ids)) != len(ids):
                raise ValueError("duplicate snapshot definition id")
        return self


class GeneratedPage(Contract):
    # Position 0 is the cover; 1..N refer to outline.pages in order.
    position: int = Field(ge=0, le=29)
    expression_type_id: str
    layout_id: str
    slots: dict[str, str | list[Content]]
    semantic_passed: bool
    structure_passed: bool
    layout_passed: bool


class GenerationCreate(Contract):
    design_snapshot: DesignSnapshot
    pages: list[GeneratedPage] = Field(min_length=6, max_length=30)

    @model_validator(mode="after")
    def valid_result(self):
        if [p.position for p in self.pages] != list(range(len(self.pages))):
            raise ValueError("generated page positions must be contiguous")
        types = {t["id"] for t in self.design_snapshot.expression_types}
        layouts = {layout["id"]: layout for layout in self.design_snapshot.layouts}
        for page in self.pages:
            layout = layouts.get(page.layout_id)
            if page.expression_type_id not in types or layout is None:
                raise ValueError("selected design is absent from snapshot")
            supported = layout.get("expression_type_ids")
            if (
                not isinstance(supported, list)
                or page.expression_type_id not in supported
            ):
                raise ValueError("unsupported expression type")
            if not all(
                (page.semantic_passed, page.structure_passed, page.layout_passed)
            ):
                raise ValueError("all pages must pass review before completion")
        return self


class GenerationRead(GenerationCreate):
    id: UUID
    presentation_id: UUID
    created_at: datetime


class RecordCreate(Contract):
    stage: str = Field(min_length=1)
    kind: Literal["candidates", "decision", "semantic_review", "validation"]
    model_id: str | None = None
    page_position: int | None = Field(default=None, ge=0, le=29)
    attempt: int = Field(default=1, ge=1, le=2)
    payload: dict[str, JsonValue]


class RecordRead(RecordCreate):
    id: UUID
    presentation_id: UUID
    created_at: datetime
