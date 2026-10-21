import asyncio
from uuid import uuid4

import pytest

from app.repositories import PresentationRepository
from app.schemas import GenerationCreate, Outline, PresentationCreate, RecordCreate


def generation():
    return GenerationCreate.model_validate(
        {
            "design_snapshot": {
                "schema_version": 1,
                "expression_types": [{"id": "message", "purpose": "핵심 전달"}],
                "layouts": [
                    {
                        "id": "message",
                        "purpose": "핵심 메시지",
                        "enabled": True,
                        "expression_type_ids": ["message"],
                        "slots": [{"id": "title", "role": "제목", "max_length": 100}],
                    }
                ],
            },
            "pages": [
                {
                    "position": i,
                    "expression_type_id": "message",
                    "layout_id": "message",
                    "slots": {"title": f"슬라이드 {i}"},
                    "semantic_passed": True,
                    "structure_passed": True,
                    "layout_passed": True,
                }
                for i in range(6)
            ],
        }
    )


def valid_outline():
    pages = [
        {"id": str(uuid4()), "title": str(i), "key_message": "핵심", "contents": []}
        for i in range(5)
    ]
    return Outline.model_validate(
        {
            "cover_title": "표지",
            "chapters": [
                {
                    "id": str(uuid4()),
                    "title": "챕터",
                    "page_ids": [p["id"] for p in pages],
                }
            ],
            "pages": pages,
        }
    )


def test_outline_rejects_invalid_membership_and_content():
    data = valid_outline().model_dump(mode="json")
    data["chapters"][0]["page_ids"].reverse()
    with pytest.raises(ValueError):
        Outline.model_validate(data)
    data = valid_outline().model_dump(mode="json")
    data["pages"][0]["contents"] = [{"title": "항목", "description": "설명"}] * 7
    with pytest.raises(ValueError):
        Outline.model_validate(data)


def test_outline_round_trip_confirmation_and_structure_preservation():
    async def scenario():
        repo = PresentationRepository()
        original = valid_outline()
        created = await repo.create(
            PresentationCreate(input_text="한국어 요청", outline=original)
        )
        edited = original.model_copy(deep=True)
        edited.pages[0].title = "사용자 수정"
        await repo.edit_outline(created.id, edited)
        changed = edited.model_copy(deep=True)
        changed.pages.reverse()
        changed.chapters[0].page_ids.reverse()
        with pytest.raises(ValueError, match="structure"):
            await repo.edit_outline(created.id, changed)
        await repo.confirm(created.id)
        restored = await repo.get(created.id)
        assert restored.outline == edited
        assert restored.status == "confirmed"
        with pytest.raises(ValueError, match="confirmed"):
            await repo.edit_outline(created.id, original)

    asyncio.run(scenario())


def test_generation_preserves_snapshot_outline_and_audit_records():
    async def scenario():
        repo = PresentationRepository()
        original = valid_outline()
        created = await repo.create(
            PresentationCreate(input_text="발표 요청", outline=original)
        )
        with pytest.raises(ValueError, match="confirmed"):
            await repo.save_generation(created.id, generation())
        await repo.confirm(created.id)
        await repo.fail(created.id, "model_call_failed")
        assert (await repo.get(created.id)).outline == original
        assert (await repo.get(created.id)).status == "failed"
        assert await repo.generations(created.id) == []
        for kind in ("candidates", "decision", "semantic_review", "validation"):
            await repo.add_record(
                created.id,
                RecordCreate(
                    stage="layout_selection",
                    kind=kind,
                    model_id="jev-1.13.0",
                    page_position=1,
                    payload={"candidate_ids": ["message"], "passed": True},
                ),
            )
        data = generation()
        saved = await repo.save_generation(created.id, data)
        data.design_snapshot.layouts[0]["purpose"] = "변경된 정의"
        data.design_snapshot.layouts[0]["enabled"] = False
        restored = (await repo.generations(created.id))[0]
        assert restored == saved
        assert restored.design_snapshot.layouts[0]["purpose"] == "핵심 메시지"
        assert (await repo.get(created.id)).outline == original
        assert (await repo.get(created.id)).status == "completed"
        records = await repo.records(created.id)
        assert {r.kind for r in records} == {
            "candidates",
            "decision",
            "semantic_review",
            "validation",
        }
        assert all(r.presentation_id == created.id for r in records)
        with pytest.raises(ValueError):
            await repo.fail(created.id, "cannot overwrite completion")

    asyncio.run(scenario())


def test_incomplete_generation_is_rejected():
    data = generation().model_dump(mode="json")
    data["pages"][1]["semantic_passed"] = False
    with pytest.raises(ValueError, match="pass review"):
        GenerationCreate.model_validate(data)


def test_database_guards_immutable_results_and_confirmed_outline():
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from app.db import transaction

    async def scenario():
        repo = PresentationRepository()
        created = await repo.create(
            PresentationCreate(input_text="요청", outline=valid_outline())
        )
        await repo.confirm(created.id)
        saved = await repo.save_generation(created.id, generation())
        for query, id in (
            (
                "UPDATE generation SET design_snapshot = '{}'::jsonb WHERE id = :id",
                saved.id,
            ),
            ("DELETE FROM generation WHERE id = :id", saved.id),
            (
                "UPDATE presentation SET outline = "
                "jsonb_set(outline, '{cover_title}', '\"변경\"') WHERE id = :id",
                created.id,
            ),
        ):
            with pytest.raises(DBAPIError):
                async with transaction() as session:
                    await session.execute(text(query), {"id": id})
        assert (await repo.generations(created.id))[0] == saved
        async with transaction() as session:
            assert await session.scalar(text("SELECT to_regclass('layout')")) is None

        with pytest.raises(DBAPIError):
            async with transaction() as session:
                await session.execute(
                    text(
                        "UPDATE generation SET presentation_id = :id "
                        "WHERE id = :generation"
                    ),
                    {"id": uuid4(), "generation": saved.id},
                )

    asyncio.run(scenario())
