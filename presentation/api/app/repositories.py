from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from app import models, schemas
from app.db import transaction


async def locked_presentation(session: AsyncSession, id: UUID) -> models.Presentation:
    row = await session.scalar(
        select(models.Presentation)
        .where(models.Presentation.id == id)
        .with_for_update()
    )
    if row is None:
        raise LookupError("presentation not found")
    return row


class PresentationRepository:
    async def create(
        self, data: schemas.PresentationCreate
    ) -> schemas.PresentationRead:
        data = schemas.PresentationCreate.model_validate(data.model_dump(mode="json"))
        async with transaction() as session:
            row = models.Presentation(**data.model_dump(mode="json"))
            session.add(row)
            await session.flush()
            return schemas.PresentationRead.model_validate(row.model_dump())

    async def get(self, id: UUID) -> schemas.PresentationRead:
        async with transaction() as session:
            row = await session.get(models.Presentation, id)
            if row is None:
                raise LookupError("presentation not found")
            return schemas.PresentationRead.model_validate(row.model_dump())

    async def edit_outline(self, id: UUID, outline: schemas.Outline) -> None:
        outline = schemas.Outline.model_validate(outline.model_dump(mode="json"))
        async with transaction() as session:
            row = await locked_presentation(session, id)
            if row.status != "editing":
                raise ValueError("confirmed outline is immutable")
            if (
                schemas.Outline.model_validate(row.outline).structure()
                != outline.structure()
            ):
                raise ValueError("outline structure must be preserved")
            row.outline = outline.model_dump(mode="json")

    async def confirm(self, id: UUID) -> None:
        async with transaction() as session:
            row = await locked_presentation(session, id)
            if row.status != "editing":
                raise ValueError("already confirmed")
            row.status = "confirmed"
            row.confirmed_at = datetime.now(UTC)

    async def fail(self, id: UUID, reason: str) -> None:
        if not reason.strip():
            raise ValueError("failure reason is required")
        async with transaction() as session:
            row = await locked_presentation(session, id)
            if row.status not in ("confirmed", "failed"):
                raise ValueError("only confirmed unfinished presentations can fail")
            row.status, row.failure = "failed", reason

    async def save_generation(
        self, id: UUID, data: schemas.GenerationCreate
    ) -> schemas.GenerationRead:
        data = schemas.GenerationCreate.model_validate(data.model_dump(mode="json"))
        async with transaction() as session:
            presentation = await locked_presentation(session, id)
            if presentation.status not in ("confirmed", "failed"):
                raise ValueError("generation requires confirmed unfinished outline")
            if len(data.pages) != len(presentation.outline["pages"]) + 1:
                raise ValueError("generation must preserve page count")
            row = models.Generation(presentation_id=id, **data.model_dump(mode="json"))
            session.add(row)
            presentation.status, presentation.failure = "completed", None
            await session.flush()
            return schemas.GenerationRead.model_validate(row.model_dump())

    async def generations(self, id: UUID) -> list[schemas.GenerationRead]:
        async with transaction() as session:
            rows = await session.scalars(
                select(models.Generation)
                .where(models.Generation.presentation_id == id)
                .order_by(col(models.Generation.created_at), col(models.Generation.id))
            )
            return [
                schemas.GenerationRead.model_validate(row.model_dump()) for row in rows
            ]

    async def add_record(
        self, id: UUID, data: schemas.RecordCreate
    ) -> schemas.RecordRead:
        data = schemas.RecordCreate.model_validate(data.model_dump(mode="json"))
        async with transaction() as session:
            presentation = await locked_presentation(session, id)
            if data.page_position is not None and data.page_position > len(
                presentation.outline["pages"]
            ):
                raise ValueError("record references an unknown page")
            row = models.Record(presentation_id=id, **data.model_dump(mode="json"))
            session.add(row)
            await session.flush()
            return schemas.RecordRead.model_validate(row.model_dump())

    async def records(self, id: UUID) -> list[schemas.RecordRead]:
        async with transaction() as session:
            rows = await session.scalars(
                select(models.Record)
                .where(models.Record.presentation_id == id)
                .order_by(col(models.Record.created_at), col(models.Record.id))
            )
            return [schemas.RecordRead.model_validate(row.model_dump()) for row in rows]
