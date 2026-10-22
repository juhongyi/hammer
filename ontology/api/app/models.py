"""Live design definitions owned only by the ontology app.

Validate aggregate writes against schemas.Catalog. Local relationships and value
ranges are also enforced by PostgreSQL. Layouts and types have stable IDs; edits
affect future generation only. Presentation stores its own complete catalog copy.
"""

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ExpressionType(SQLModel, table=True):
    __tablename__ = "expression_type"
    __table_args__ = (
        CheckConstraint("length(trim(id)) > 0", name="type_id_not_empty"),
        CheckConstraint("length(trim(purpose)) > 0", name="type_purpose_not_empty"),
        CheckConstraint(
            "jsonb_typeof(suitable_when) = 'array' "
            "AND jsonb_array_length(suitable_when) > 0",
            name="type_suitability_required",
        ),
    )

    id: str = Field(primary_key=True)
    purpose: str
    suitable_when: list[str] = Field(sa_type=JSONB)
    unsuitable_when: list[str] = Field(default_factory=list, sa_type=JSONB)
    enabled: bool = Field(default=False)


class Layout(SQLModel, table=True):
    __table_args__ = (
        CheckConstraint("length(trim(id)) > 0", name="layout_id_not_empty"),
        CheckConstraint("length(trim(purpose)) > 0", name="layout_purpose_not_empty"),
        CheckConstraint(
            "length(trim(structure)) > 0", name="layout_structure_not_empty"
        ),
    )

    id: str = Field(primary_key=True)
    purpose: str
    structure: str
    required_content: list[str] = Field(default_factory=list, sa_type=JSONB)
    enabled: bool = Field(default=False)


class LayoutSupport(SQLModel, table=True):
    __tablename__ = "layout_support"

    layout_id: str = Field(foreign_key="layout.id", primary_key=True)
    expression_type_id: str = Field(foreign_key="expression_type.id", primary_key=True)


class Slot(SQLModel, table=True):
    """Slot IDs are scoped to their layout; repeated slots share repeat_group."""

    __table_args__ = (
        UniqueConstraint("layout_id", "position"),
        CheckConstraint("length(trim(id)) > 0", name="slot_id_not_empty"),
        CheckConstraint("length(trim(role)) > 0", name="slot_role_not_empty"),
        CheckConstraint("position >= 0", name="slot_position"),
        CheckConstraint("data_type IN ('text', 'items')", name="slot_data_type"),
        CheckConstraint(
            "min_items >= 0 AND max_items >= 1 AND min_items <= max_items",
            name="slot_item_range",
        ),
        CheckConstraint("max_characters >= 1", name="slot_character_capacity"),
        CheckConstraint(
            "data_type != 'text' OR max_items = 1", name="text_slot_single_value"
        ),
        CheckConstraint("NOT required OR min_items >= 1", name="required_slot_content"),
    )

    layout_id: str = Field(foreign_key="layout.id", primary_key=True)
    id: str = Field(primary_key=True)
    role: str
    data_type: str
    required: bool
    position: int
    repeat_group: str | None = None
    required_content: list[str] = Field(default_factory=list, sa_type=JSONB)
    min_items: int = Field(default=0)
    max_items: int
    max_characters: int
