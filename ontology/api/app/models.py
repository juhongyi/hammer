"""Ontology entities are local to the ontology database."""

from sqlalchemy import CheckConstraint, Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


class ExpressionType(SQLModel, table=True):
    __tablename__ = "expression_type"
    id: str = Field(primary_key=True)
    purpose: str
    suitable: str
    unsuitable: str
    enabled: bool


class Layout(SQLModel, table=True):
    __tablename__ = "layout"
    __table_args__ = (CheckConstraint("min_items >= 0 AND max_items >= min_items"),)
    id: str = Field(primary_key=True)
    purpose: str
    required_content: list[str] = Field(sa_column=Column(JSONB, nullable=False))
    min_items: int
    max_items: int
    enabled: bool


class Support(SQLModel, table=True):
    __tablename__ = "layout_support"
    layout_id: str = Field(
        primary_key=True, foreign_key="layout.id", ondelete="CASCADE"
    )
    expression_type_id: str = Field(primary_key=True, foreign_key="expression_type.id")


class Slot(SQLModel, table=True):
    __tablename__ = "slot"
    __table_args__ = (
        UniqueConstraint("layout_id", "position"),
        CheckConstraint("position >= 0"),
        CheckConstraint("data_type IN ('text', 'items')"),
        CheckConstraint("min_items >= 0 AND max_items >= 1 AND max_items >= min_items"),
        CheckConstraint("max_length > 0"),
    )
    layout_id: str = Field(
        primary_key=True, foreign_key="layout.id", ondelete="CASCADE"
    )
    id: str = Field(primary_key=True)
    role: str
    data_type: str
    required: bool
    position: int
    min_items: int
    max_items: int
    max_length: int
