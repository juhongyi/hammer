from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Item(StrictModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=600)


class Cover(StrictModel):
    id: Literal["cover"] = "cover"
    title: str = Field(min_length=1, max_length=160)


class Page(StrictModel):
    id: str
    title: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=400)
    items: list[Item] = Field(max_length=6)


class Draft(StrictModel):
    cover: Cover
    pages: list[Page] = Field(min_length=5, max_length=29)


class Chapter(StrictModel):
    id: str
    title: str = Field(min_length=1, max_length=120)
    page_ids: list[str] = Field(min_length=1)


class Outline(Draft):
    chapters: list[Chapter] = Field(min_length=1, max_length=29)


class ExpressionType(StrictModel):
    id: str
    purpose: str = Field(min_length=1, max_length=2000)
    suitable: str = Field(min_length=1, max_length=2000)
    unsuitable: str = Field(min_length=1, max_length=2000)


class Slot(StrictModel):
    id: str
    role: str = Field(min_length=1, max_length=1000)
    kind: Literal["text", "items"]
    required: bool
    max_length: int = Field(ge=1, le=600)
    min_items: int = Field(default=0, ge=0, le=6)
    max_items: int = Field(default=0, ge=0, le=6)
    item_title_max_length: int = Field(default=32, ge=1, le=120)


class Layout(StrictModel):
    id: str
    purpose: str = Field(min_length=1, max_length=2000)
    supported_types: list[str] = Field(min_length=1)
    enabled: bool
    slots: list[Slot] = Field(min_length=1)


class Ontology(StrictModel):
    types: list[ExpressionType]
    layouts: list[Layout]


class Input(StrictModel):
    text: str = Field(min_length=1, max_length=16000)


class Confirmation(StrictModel):
    outline: Outline
