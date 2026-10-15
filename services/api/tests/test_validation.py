import asyncio
from copy import deepcopy

import pytest

from app.models import Models, ModelError, TextError
from app.ontology import candidates, initial_ontology, validate_ontology
from app.render import Renderer, slide_html
from app.schemas import Draft, Outline
from app.validation import validate_copy, validate_outline
from test_pipeline import draft


def test_rejects_chapter_duplication_and_missing_page():
    value = {**draft(), "chapters": [{"id": "c1", "title": "챕터", "page_ids": ["p1", "p2", "p2", "p4", "p5"]}]}
    with pytest.raises(TextError):
        validate_outline(Outline.model_validate(value), 6, 1)


def test_candidate_filter_does_not_preemptively_reject_long_outline_text():
    ontology = initial_ontology()
    page = draft()["pages"][0]
    page["message"] = "긴 내용 " * 100
    assert [l.id for l in candidates(ontology, "list", page)] == ["list"]
    assert candidates(ontology, "comparison", page) == []
    ontology.layouts[2].enabled = False
    assert candidates(ontology, "list", page) == []


@pytest.mark.parametrize("mutation", ["new_slot", "length", "unknown_type", "invalid_count", "required", "cover_relation"])
def test_ontology_validation_keeps_fixed_renderer_contract(mutation):
    ontology = initial_ontology()
    slot = ontology.layouts[2].slots[2]
    if mutation == "new_slot": slot.id = "unknown"
    if mutation == "length": slot.max_length += 1
    if mutation == "unknown_type": ontology.layouts[2].supported_types = ["missing"]
    if mutation == "invalid_count": slot.min_items = 5; slot.max_items = 2
    if mutation == "required": slot.required = True
    if mutation == "cover_relation": ontology.layouts[0].supported_types = ["list"]
    with pytest.raises(ValueError):
        validate_ontology(ontology)


@pytest.mark.parametrize("mutation", ["number", "unit", "missing_slot", "long_text", "blank", "extra_item"])
def test_copy_checks_numeric_units_slots_capacity_and_item_count(mutation):
    page = draft()["pages"][0]
    layout = initial_ontology().layouts[2]
    copy = {k: deepcopy(page[k]) for k in ("title", "message", "items")}
    if mutation == "number": copy["items"][0]["description"] = "30% 개선"
    if mutation == "unit": copy["items"][0]["description"] = "20명 개선"
    if mutation == "missing_slot": del copy["message"]
    if mutation == "long_text": copy["title"] = "가" * 65
    if mutation == "blank": copy["title"] = "  "
    if mutation == "extra_item": copy["items"] *= 2
    with pytest.raises(TextError):
        validate_copy(copy, page, layout)


def test_real_renderer_rejects_overflow_and_escapes_html():
    slide = {"layout": initial_ontology().layouts[0].model_dump(), "copy": {"title": "<script>alert('test')</script>"}}
    assert "<script>" not in slide_html(slide)
    async def check():
        async with Renderer() as renderer:
            await renderer.check(slide)
            slide["copy"]["title"] = "잘림 검사\n" * 30
            with pytest.raises(TextError, match="잘림"):
                await renderer.check(slide)
    asyncio.run(check())


def test_numeric_time_units_cannot_change_with_same_value():
    page = draft()["pages"][0]
    page["items"][0]["description"] = "회의 시간 60분"
    copy = {k: deepcopy(page[k]) for k in ("title", "message", "items")}
    copy["items"][0]["description"] = "회의 시간 60시간"
    with pytest.raises(TextError, match="수치·단위"):
        validate_copy(copy, page, initial_ontology().layouts[2])


def test_all_six_fixed_layouts_render_without_clipping_at_supported_item_counts():
    async def check():
        async with Renderer() as renderer:
            for layout in initial_ontology().layouts:
                copy = {"title": "한국어 발표 제목"}
                if layout.id != "cover":
                    copy["message"] = "개요의 핵심 메시지를 전달합니다."
                    count = layout.slots[2].max_items
                    copy["items"] = [{"title": "항목 제목", "description": "명확한 한국어 설명을 전달합니다."} for _ in range(count)]
                await renderer.check({"layout": layout.model_dump(), "copy": copy})
    asyncio.run(check())


@pytest.mark.parametrize("answer", [
    {"type": "choice", "choice": "not-a-candidate", "confidence": 1, "probabilities": {"yes": 1}},
    {"type": "choice", "choice": "yes", "confidence": 1, "probabilities": {"yes": 0.2}},
    {"type": "choice", "choice": "yes", "confidence": float("nan"), "probabilities": {"yes": 1}},
    {},
])
def test_invalid_jev_results_fail_without_fallback(answer):
    models = Models()
    async def post(*args):
        return {"answers": {"decision": answer}}
    models.post = post
    with pytest.raises(ModelError):
        asyncio.run(models.choice({}, "선택", {"yes": "후보"}))


def test_workers_ai_requests_json_and_preserves_truncation_error(monkeypatch):
    monkeypatch.setenv("CLOUDFLARE_ACCOUNT_ID", "test-account")
    models = Models()
    calls = []
    async def post(url, key, body):
        calls.append((url, body))
        return {"choices": [{"finish_reason": "length", "message": {"content": ""}}]}
    models.post = post
    with pytest.raises(TextError, match="토큰 한도"):
        asyncio.run(models.text("문구 작성", {}, {"title": "제목"}))
    assert calls[0][0].endswith("/test-account/ai/v1/chat/completions")
    assert calls[0][1]["response_format"] == {"type": "json_object"}
    assert calls[0][1]["reasoning_effort"] == "low"
