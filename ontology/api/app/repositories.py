from sqlalchemy import delete, text
from sqlmodel import col, select

from app import models, schemas
from app.db import transaction


class OntologyRepository:
    async def save(self, definition: schemas.OntologyDefinition) -> None:
        """Upsert the supplied definitions atomically; omitted entities are retained."""
        definition = schemas.OntologyDefinition.model_validate(
            definition.model_dump(mode="json")
        )
        async with transaction() as session:
            for item in definition.expression_types:
                await session.merge(models.ExpressionType(**item.model_dump()))
            await session.flush()
            for item in definition.layouts:
                await session.merge(
                    models.Layout(
                        **item.model_dump(exclude={"slots", "expression_type_ids"})
                    )
                )
                await session.flush()
                # Lock the parent before replacing its relationships.
                await session.execute(
                    select(models.Layout)
                    .where(models.Layout.id == item.id)
                    .with_for_update()
                )
                await session.execute(
                    delete(models.Slot).where(col(models.Slot.layout_id) == item.id)
                )
                await session.execute(
                    delete(models.Support).where(
                        col(models.Support.layout_id) == item.id
                    )
                )
                for type_id in item.expression_type_ids:
                    session.add(
                        models.Support(layout_id=item.id, expression_type_id=type_id)
                    )
                for slot in item.slots:
                    session.add(models.Slot(layout_id=item.id, **slot.model_dump()))

    async def get(self) -> schemas.OntologyDefinition:
        async with transaction() as session:
            # One repeatable-read snapshot across all relationship queries.
            await session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            )
            types = (
                await session.scalars(
                    select(models.ExpressionType).order_by(models.ExpressionType.id)
                )
            ).all()
            layouts = (
                await session.scalars(select(models.Layout).order_by(models.Layout.id))
            ).all()
            slots = (
                await session.scalars(
                    select(models.Slot).order_by(col(models.Slot.position))
                )
            ).all()
            supports = (
                await session.scalars(
                    select(models.Support).order_by(models.Support.expression_type_id)
                )
            ).all()
            return schemas.OntologyDefinition(
                expression_types=[
                    schemas.ExpressionType.model_validate(t.model_dump()) for t in types
                ],
                layouts=[
                    schemas.Layout(
                        **layout.model_dump(),
                        expression_type_ids=[
                            s.expression_type_id
                            for s in supports
                            if s.layout_id == layout.id
                        ],
                        slots=[
                            schemas.Slot.model_validate(
                                s.model_dump(exclude={"layout_id"})
                            )
                            for s in slots
                            if s.layout_id == layout.id
                        ],
                    )
                    for layout in layouts
                ],
            )
