from typing import Annotated, Literal, Self
from uuid import UUID, uuid4

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    model_validator,
)

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Health(BaseModel):
    status: Literal["ok"]


class PresentationRequest(Contract):
    input_text: Text


class ContentItem(Contract):
    title: Text
    description: Text


class Page(Contract):
    id: UUID = Field(default_factory=uuid4)
    title: Text
    key_message: Text
    contents: list[ContentItem] = Field(max_length=6)


class Chapter(Contract):
    id: UUID = Field(default_factory=uuid4)
    title: Text
    pages: list[Page] = Field(min_length=1)


class Outline(Contract):
    """List order is page order; the cover is slide 1, outside all chapters."""

    cover_title: Text
    chapters: list[Chapter] = Field(min_length=1, max_length=29)

    @property
    def slide_count(self) -> int:
        return 1 + sum(len(chapter.pages) for chapter in self.chapters)

    @property
    def structure(self) -> tuple[tuple[UUID, tuple[UUID, ...]], ...]:
        return tuple((c.id, tuple(p.id for p in c.pages)) for c in self.chapters)

    @model_validator(mode="after")
    def validate_structure(self) -> Self:
        if not 6 <= self.slide_count <= 30:
            raise ValueError("An outline must contain 6–30 slides including the cover")
        chapter_ids = [c.id for c in self.chapters]
        page_ids = [p.id for c in self.chapters for p in c.pages]
        if len(set(chapter_ids)) != len(chapter_ids):
            raise ValueError("Chapter IDs must be unique")
        if len(set(page_ids)) != len(page_ids):
            raise ValueError("Every body page must belong to exactly one chapter")
        return self


class OutlineEdit(Contract):
    """The persisted original must be supplied by the application, not the client."""

    original: Outline
    edited: Outline

    @model_validator(mode="after")
    def preserve_structure(self) -> Self:
        if self.original.structure != self.edited.structure:
            raise ValueError("Editing must preserve chapter membership and page order")
        return self


class PresentationData(Contract):
    id: UUID
    input_text: Text
    status: Literal["editing", "confirmed"]
    outline: Outline | None = None
    confirmed_outline: Outline | None = None
    created_at: AwareDatetime

    @model_validator(mode="after")
    def validate_confirmation(self) -> Self:
        if self.status == "confirmed":
            if self.confirmed_outline is None or self.outline != self.confirmed_outline:
                raise ValueError(
                    "Confirmation must preserve the complete edited outline"
                )
        elif self.confirmed_outline is not None:
            raise ValueError("An editing presentation cannot have a confirmed outline")
        return self


class DesignSnapshot(Contract):
    """Copy of the ontology Catalog contract, never a live cross-database reference.

    catalog contains the complete serialized Catalog, including expression types,
    layouts, support relations, slots and constraints. Validate it against the
    ontology contract when it is received; retain it unchanged with the result.
    """

    id: UUID = Field(default_factory=uuid4)
    schema_version: Literal[1] = 1
    captured_at: AwareDatetime
    catalog: dict[str, JsonValue]

    @model_validator(mode="after")
    def validate_catalog_envelope(self) -> Self:
        if self.catalog.get("schema_version") != self.schema_version:
            raise ValueError("Catalog schema version must match the snapshot")
        for key in ("expression_types", "layouts"):
            if not isinstance(self.catalog.get(key), list):
                raise ValueError(f"Catalog must contain {key}")
        return self


class GeneratedSlide(Contract):
    # 1 is the cover; body pages follow the confirmed outline's flattened order.
    position: int = Field(ge=1, le=30)
    page_id: UUID | None = None
    expression_type_id: Text
    layout_id: Text
    slots: dict[str, JsonValue]


class GenerationResult(Contract):
    confirmed_outline: Outline
    design_snapshot: DesignSnapshot
    status: Literal["generating", "completed", "failed"]
    slides: list[GeneratedSlide] = Field(default_factory=list, max_length=30)
    error: Text | None = None

    @model_validator(mode="after")
    def validate_result(self) -> Self:
        page_order = [None] + [
            p.id for c in self.confirmed_outline.chapters for p in c.pages
        ]
        positions = [s.position for s in self.slides]
        if len(set(positions)) != len(positions):
            raise ValueError("Slide positions must be unique")
        if positions != sorted(positions):
            raise ValueError("Slides must follow the confirmed order")
        for slide in self.slides:
            if slide.position > len(page_order):
                raise ValueError("Slide exceeds the confirmed slide count")
            if slide.page_id != page_order[slide.position - 1]:
                raise ValueError("Slide must reference its confirmed page")
        if self.status == "completed" and positions != list(
            range(1, len(page_order) + 1)
        ):
            raise ValueError("Only a complete deck can be marked completed")
        if (self.status == "failed") != (self.error is not None):
            raise ValueError("Only a failed generation must contain an error")
        return self


class Candidate(Contract):
    id: Text
    definition: dict[str, JsonValue]


class DecisionRecord(Contract):
    stage: Literal[
        "slide_count",
        "chapter_count",
        "chapter_boundaries",
        "expression_type",
        "layout",
        "outline_review",
        "text_review",
        "structure_review",
        "render_review",
    ]
    page_id: UUID | None = None
    attempt: int = Field(ge=1, le=2)
    provider: Text
    model: Text
    candidates: list[Candidate] = Field(default_factory=list)
    selected_id: Text | None = None
    verdict: Literal["passed", "failed", "error"] | None = None
    details: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_selection(self) -> Self:
        ids = [candidate.id for candidate in self.candidates]
        if len(set(ids)) != len(ids):
            raise ValueError("Candidate IDs must be unique")
        if self.selected_id is not None and self.selected_id not in ids:
            raise ValueError("Selection must refer to a recorded candidate")
        return self
