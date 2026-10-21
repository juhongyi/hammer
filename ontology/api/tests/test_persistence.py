import asyncio
from uuid import uuid4

import pytest

from app.repositories import OntologyRepository
from app.schemas import ExpressionType, Layout, OntologyDefinition, Slot


def definition():
    suffix = uuid4().hex
    return OntologyDefinition(
        expression_types=[
            ExpressionType(
                id=f"message-{suffix}",
                purpose="핵심 전달",
                suitable="요약",
                unsuitable="비교",
            )
        ],
        layouts=[
            Layout(
                id=f"message-{suffix}",
                purpose="핵심 메시지",
                expression_type_ids=[f"message-{suffix}"],
                slots=[Slot(id="title", role="제목", data_type="text", position=0)],
            )
        ],
    )


def test_definition_round_trip_and_update():
    async def scenario():
        repo = OntologyRepository()
        original = definition()
        await repo.save(original)
        restored = await repo.get()
        assert original.layouts[0] in restored.layouts
        assert original.expression_types[0] in restored.expression_types
        original.layouts[0].enabled = False
        original.layouts[0].slots[0].max_length = 20
        await repo.save(original)
        restored = await repo.get()
        assert original.layouts[0] in restored.layouts

    asyncio.run(scenario())


def test_invalid_support_and_capacity_are_rejected():
    data = definition().model_dump(mode="json")
    data["layouts"][0]["expression_type_ids"] = ["unknown"]
    with pytest.raises(ValueError, match="unknown expression type"):
        OntologyDefinition.model_validate(data)
    data = definition().model_dump(mode="json")
    data["layouts"][0]["slots"][0]["min_items"] = 2
    with pytest.raises(ValueError, match="min_items"):
        OntologyDefinition.model_validate(data)


def test_database_enforces_support_foreign_keys_and_slot_capacity():
    from sqlalchemy import text
    from sqlalchemy.exc import IntegrityError

    from app.db import transaction

    async def scenario():
        repo = OntologyRepository()
        data = definition()
        await repo.save(data)
        for query in (
            "UPDATE layout_support SET expression_type_id = 'missing' "
            "WHERE layout_id = :id",
            "UPDATE slot SET max_length = 0 WHERE layout_id = :id",
        ):
            with pytest.raises(IntegrityError):
                async with transaction() as session:
                    await session.execute(text(query), {"id": data.layouts[0].id})
        async with transaction() as session:
            assert (
                await session.scalar(text("SELECT to_regclass('presentation')")) is None
            )

    asyncio.run(scenario())
