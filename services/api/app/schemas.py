from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ExpressionId = Literal[
    "introduction", "emphasis", "enumeration", "comparison", "process", "closing"
]
LayoutId = Literal["cover", "message", "list", "comparison", "process", "closing"]
Status = Literal[
    "outline_ready", "queued", "generating", "awaiting_validation", "completed", "failed"
]

CAPACITIES = {
    "cover": (0, 1, 120),
    "message": (0, 2, 160),
    "list": (2, 6, 100),
    "comparison": (2, 2, 180),
    "process": (3, 5, 80),
    "closing": (0, 2, 120),
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExpressionType(StrictModel):
    id: ExpressionId
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)


class TextSlot(StrictModel):
    role: Literal["title", "key_message"]
    content_kind: Literal["text"] = "text"
    description: str = Field(min_length=1)
    max_chars: int = Field(ge=1)


class BodySlot(StrictModel):
    role: Literal["body"] = "body"
    content_kind: Literal["heading_text_blocks"] = "heading_text_blocks"
    description: str = Field(min_length=1)
    min_items: int = Field(ge=0)
    max_items: int = Field(ge=0)
    heading_max_chars: int = Field(ge=1, le=32)
    text_max_chars: int = Field(ge=1)


class Slots(StrictModel):
    title: TextSlot
    key_message: TextSlot
    body: BodySlot


class Layout(StrictModel):
    id: LayoutId
    name: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    supports: list[ExpressionId] = Field(min_length=1)
    enabled: bool
    slots: Slots

    @model_validator(mode="after")
    def validate_renderer_bounds(self):
        minimum, maximum, text_max = CAPACITIES[self.id]
        body = self.slots.body
        if not minimum <= body.min_items <= body.max_items <= maximum:
            raise ValueError("본문 블록 범위가 고정 레이아웃의 수용 범위를 벗어납니다.")
        if body.text_max_chars > text_max:
            raise ValueError("본문 글자 수가 고정 레이아웃의 상한을 넘습니다.")
        if self.slots.title.role != "title" or self.slots.key_message.role != "key_message":
            raise ValueError("슬롯 역할을 변경할 수 없습니다.")
        if self.slots.title.max_chars > 48 or self.slots.key_message.max_chars > 96:
            raise ValueError("제목 또는 핵심 메시지의 글자 수가 렌더러 상한을 넘습니다.")
        if len(self.supports) != len(set(self.supports)):
            raise ValueError("지원 관계가 중복되었습니다.")
        return self


class Catalogue(StrictModel):
    version: int = Field(ge=1)
    types: list[ExpressionType]
    layouts: list[Layout]

    @model_validator(mode="after")
    def validate_fixed_catalogue(self):
        type_ids = [item.id for item in self.types]
        layout_ids = [item.id for item in self.layouts]
        if len(type_ids) != 6 or set(type_ids) != {
            "introduction",
            "emphasis",
            "enumeration",
            "comparison",
            "process",
            "closing",
        }:
            raise ValueError("준비된 표현 유형 6개의 식별자를 유지해야 합니다.")
        if len(layout_ids) != 6 or set(layout_ids) != set(CAPACITIES):
            raise ValueError("준비된 레이아웃 6개의 식별자를 유지해야 합니다.")
        return self


class OutlinePage(StrictModel):
    title: str = Field(min_length=1)
    key_message: str = Field(min_length=1)
    main_content: str = Field(min_length=1)


class Outline(StrictModel):
    pages: list[OutlinePage] = Field(min_length=6, max_length=30)


class TextInput(StrictModel):
    text: str = Field(min_length=1)


class Block(StrictModel):
    heading: str = Field(min_length=1, max_length=32)
    text: str = Field(min_length=1, max_length=180)


class SlideContent(StrictModel):
    title: str = Field(min_length=1, max_length=48)
    key_message: str = Field(min_length=1, max_length=96)
    blocks: list[Block] = Field(max_length=6)


class ChoiceResult(StrictModel):
    choice: str
    probabilities: dict[str, float]
    confidence: float = Field(ge=0, le=1)
    model: str
    usage: dict[str, int]


class RankedCandidate(StrictModel):
    layout_id: str
    name: str
    probability: float


class DecisionTrace(StrictModel):
    faithfulness: ChoiceResult | None = None
    faithfulness_request: dict[str, Any] | None = None
    planning: ChoiceResult | None = None
    planning_request: dict[str, Any] | None = None
    writing_schema: dict[str, Any] | None = None
    classification: ChoiceResult
    selection: ChoiceResult
    ranked_candidates: list[RankedCandidate]
    classification_request: dict[str, Any]
    selection_request: dict[str, Any]


class SlideResult(StrictModel):
    index: int
    content: SlideContent
    layout: Layout
    trace: DecisionTrace


class PresentationSummary(StrictModel):
    id: str
    title: str
    status: Status
    page_count: int
    created_at: str


class PresentationView(StrictModel):
    id: str
    source: str
    outline: Outline
    status: Status
    phase: str
    error: str | None
    run_id: str | None
    slides: list[SlideResult]
    snapshot: Catalogue | None
    created_at: str


class PageValidation(StrictModel):
    index: int = Field(ge=0)
    issues: list[str]


class RenderValidation(StrictModel):
    run_id: str
    font_loaded: bool
    pages: list[PageValidation]
