from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(min_length=1, pattern=r"\S")]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Health(BaseModel):
    status: Literal["ok"]


class ExpressionTypeDefinition(Contract):
    id: Text
    purpose: Text
    suitable_when: list[Text] = Field(min_length=1)
    unsuitable_when: list[Text]
    enabled: bool = False


class ContentConstraints(Contract):
    required_content: list[Text] = Field(default_factory=list)
    min_items: int = Field(default=0, ge=0)
    max_items: int = Field(ge=1)
    max_characters: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_range(self) -> Self:
        if self.min_items > self.max_items:
            raise ValueError("min_items must not exceed max_items")
        return self


class SlotDefinition(Contract):
    id: Text
    role: Text
    data_type: Literal["text", "items"]
    required: bool
    position: int = Field(ge=0)
    repeat_group: Text | None = None
    constraints: ContentConstraints

    @model_validator(mode="after")
    def validate_shape(self) -> Self:
        if self.data_type == "text" and self.constraints.max_items != 1:
            raise ValueError("A text slot holds one value")
        if self.required and self.constraints.min_items < 1:
            raise ValueError("A required slot must contain at least one value")
        return self


class LayoutDefinition(Contract):
    id: Text
    purpose: Text
    expression_type_ids: list[Text] = Field(min_length=1)
    required_content: list[Text]
    structure: Text
    enabled: bool = False
    slots: list[SlotDefinition] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_relations(self) -> Self:
        ids = [slot.id for slot in self.slots]
        positions = [slot.position for slot in self.slots]
        if len(set(ids)) != len(ids) or len(set(positions)) != len(positions):
            raise ValueError("Slot IDs and positions must be unique within a layout")
        if positions != list(range(len(positions))):
            raise ValueError("Slots must be in contiguous zero-based order")
        if len(set(self.expression_type_ids)) != len(self.expression_type_ids):
            raise ValueError("Support relations must be unique")
        return self


class Catalog(Contract):
    """Serializable definition copied into a presentation's DesignSnapshot."""

    schema_version: Literal[1] = 1
    expression_types: list[ExpressionTypeDefinition]
    layouts: list[LayoutDefinition]

    @model_validator(mode="after")
    def validate_support(self) -> Self:
        types = {item.id: item for item in self.expression_types}
        if len(types) != len(self.expression_types):
            raise ValueError("Expression type IDs must be unique")
        if len({item.id for item in self.layouts}) != len(self.layouts):
            raise ValueError("Layout IDs must be unique")
        for layout in self.layouts:
            if any(key not in types for key in layout.expression_type_ids):
                raise ValueError("Every support relation must reference a known type")
            if layout.enabled and not any(
                types[key].enabled for key in layout.expression_type_ids
            ):
                raise ValueError("An enabled layout must support an enabled type")
        return self
