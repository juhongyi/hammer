import pytest
from pydantic import ValidationError

from app.catalogue import candidates, initial_catalogue
from app.generation import content_schema, preserves_numbers
from app.schemas import Catalogue, OutlinePage, SlideContent


def content():
    return SlideContent(
        title="두 방식 비교",
        key_message="작업 시간이 줄어듭니다.",
        blocks=[
            {"heading": "기존", "text": "하루 2시간"},
            {"heading": "개선", "text": "하루 30분"},
        ],
    )


def test_filter_enforces_support_enabled_and_shared_slot_limits():
    catalogue = initial_catalogue()
    assert {layout.id for layout in candidates(content(), "comparison", catalogue)} == {
        "comparison",
        "list",
    }
    comparison = next(layout for layout in catalogue.layouts if layout.id == "comparison")
    comparison.enabled = False
    assert [layout.id for layout in candidates(content(), "comparison", catalogue)] == ["list"]
    listing = next(layout for layout in catalogue.layouts if layout.id == "list")
    listing.slots.body.text_max_chars = 2
    assert candidates(content(), "comparison", catalogue) == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda data: data["layouts"][0]["slots"]["body"].update(max_items=2),
        lambda data: data["layouts"][0].update(supports=[]),
        lambda data: data["layouts"][0]["slots"]["title"].update(role="key_message"),
        lambda data: data["types"].pop(),
        lambda data: data["layouts"][0]["slots"]["title"].update(max_chars=49),
    ],
)
def test_invalid_relations_and_renderer_bounds_cannot_be_published(mutation):
    document = initial_catalogue().model_dump()
    mutation(document)
    with pytest.raises(ValidationError):
        Catalogue.model_validate(document)


def test_missing_or_changed_numbers_are_rejected():
    page = OutlinePage(
        title="비교", key_message="시간 단축", main_content="2시간에서 30분으로 단축"
    )
    assert preserves_numbers(page, content())
    changed = content()
    changed.blocks[1].text = "하루 20분"
    assert not preserves_numbers(page, changed)
    invented = content()
    invented.blocks[0].text = "하루 2시간, 24/7 고객 지원"
    assert not preserves_numbers(page, invented)


def test_jev_guided_writing_schema_enforces_intro_single_block_before_final_choice():
    cover = initial_catalogue().layouts[0]
    schema = content_schema([cover])
    assert (
        schema.model_validate(
            {
                "title": "소개",
                "key_message": "발표의 방향을 소개합니다.",
                "blocks": [{"heading": "목적", "text": "초기 설정 경험을 개선합니다."}],
            }
        ).root.title
        == "소개"
    )
    with pytest.raises(ValidationError):
        schema.model_validate(content().model_dump())


def test_writing_schema_preserves_exact_alternative_capacities_and_operator_changes():
    catalogue = initial_catalogue()
    alternatives = [layout for layout in catalogue.layouts if "comparison" in layout.supports]
    content_model = content_schema(alternatives)
    longer = content()
    longer.blocks[0].text = "가" * 150
    assert content_model.model_validate(longer.model_dump())
    narrower = next(layout for layout in alternatives if layout.id == "list")
    with pytest.raises(ValidationError):
        content_schema([narrower]).model_validate(longer.model_dump())
