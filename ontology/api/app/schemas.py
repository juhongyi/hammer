from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Health(BaseModel):
    status: Literal["ok"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExpressionType(Contract):
    id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    suitable: str = Field(min_length=1)
    unsuitable: str = Field(min_length=1)
    enabled: bool = True


class Slot(Contract):
    id: str = Field(min_length=1)
    role: str = Field(min_length=1)
    data_type: Literal["text", "items"]
    required: bool = True
    position: int = Field(ge=0)
    min_items: int = Field(default=0, ge=0)
    max_items: int = Field(default=1, ge=1)
    max_length: int = Field(default=200, ge=1)

    @model_validator(mode="after")
    def valid_capacity(self):
        if self.min_items > self.max_items:
            raise ValueError("min_items exceeds max_items")
        return self


class Layout(Contract):
    id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    expression_type_ids: list[str] = Field(min_length=1)
    required_content: list[str] = Field(default_factory=list)
    min_items: int = Field(default=0, ge=0)
    max_items: int = Field(default=6, ge=0)
    enabled: bool = True
    slots: list[Slot] = Field(min_length=1)

    @model_validator(mode="after")
    def valid_structure(self):
        if self.min_items > self.max_items:
            raise ValueError("min_items exceeds max_items")
        if len(set(self.expression_type_ids)) != len(self.expression_type_ids):
            raise ValueError("duplicate support relationship")
        if len({s.id for s in self.slots}) != len(self.slots):
            raise ValueError("duplicate slot id")
        if sorted(s.position for s in self.slots) != list(range(len(self.slots))):
            raise ValueError("slot positions must be contiguous")
        return self


class OntologyDefinition(Contract):
    schema_version: Literal[1] = 1
    expression_types: list[ExpressionType]
    layouts: list[Layout]

    @model_validator(mode="after")
    def valid_relationships(self):
        types = {t.id for t in self.expression_types}
        if len(types) != len(self.expression_types):
            raise ValueError("duplicate expression type")
        if len({layout.id for layout in self.layouts}) != len(self.layouts):
            raise ValueError("duplicate layout")
        for layout in self.layouts:
            if not set(layout.expression_type_ids) <= types:
                raise ValueError("unknown expression type")
        return self
