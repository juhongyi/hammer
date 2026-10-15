import json
import re

from .models import TextError
from .schemas import Draft, Layout, Outline


def nonblank(value):
    if isinstance(value, str) and not value.strip():
        raise TextError("빈 문자열이나 공백만 있는 필드는 허용하지 않습니다.")
    if isinstance(value, dict):
        for child in value.values():
            nonblank(child)
    if isinstance(value, list):
        for child in value:
            nonblank(child)


def validate_draft(draft: Draft, count: int):
    nonblank(draft.model_dump())
    if len(draft.pages) != count - 1 or [p.id for p in draft.pages] != [f"p{i}" for i in range(1, count)]:
        raise TextError("장수 또는 페이지 ID·순서가 변경되었습니다.")


def validate_outline(outline: Outline, count: int, chapter_count: int):
    validate_draft(outline, count)
    if len(outline.chapters) != chapter_count:
        raise TextError("챕터 수가 변경되었습니다.")
    if [c.id for c in outline.chapters] != [f"c{i}" for i in range(1, chapter_count + 1)]:
        raise TextError("챕터 ID·순서가 변경되었습니다.")
    if [id_ for c in outline.chapters for id_ in c.page_ids] != [p.id for p in outline.pages]:
        raise TextError("본문 페이지는 순서대로 중복·누락 없이 연속 챕터에 소속되어야 합니다.")


def structure(outline: Outline):
    return ([p.id for p in outline.pages], [(c.id, c.page_ids) for c in outline.chapters])


def numbers(value: dict) -> set[str]:
    # Only content fields, never page IDs, geometry or array indexes. Keep units
    # such as %, 년, 원 so that 10% -> 10명 cannot pass the mechanical check.
    content = {k: v for k, v in value.items() if k in ("title", "message", "items")}
    text = json.dumps(content, ensure_ascii=False)
    return {n.replace(",", "") for n in re.findall(
        r"[-+]?\d[\d,]*(?:\.\d+)?(?:%|퍼센트|억원|만원|천원|시간|분|초|억|만|천|원|명|개|년|월|일|배)?", text
    )}


def validate_copy(copy: dict, page: dict, layout: Layout):
    nonblank(copy)
    if set(copy) != {s.id for s in layout.slots}:
        raise TextError("선택된 슬롯 ID만 정확히 출력해야 합니다.")
    for slot in layout.slots:
        value = copy[slot.id]
        if slot.kind == "text":
            if not isinstance(value, str) or len(value) > slot.max_length or (slot.required and not value.strip()):
                raise TextError(f"{slot.id}: 필수 문자열·최대 {slot.max_length}자를 지켜야 합니다.")
        else:
            if not isinstance(value, list) or not slot.min_items <= len(value) <= slot.max_items:
                raise TextError(f"{slot.id}: 항목 수 제약 위반입니다.")
            if len(value) != len(page.get("items", [])):
                raise TextError("개요에 있는 항목만 같은 수와 순서로 작성해야 합니다.")
            for item in value:
                if not isinstance(item, dict) or set(item) != {"title", "description"}:
                    raise TextError("항목에는 title과 description 문자열이 필요합니다.")
                if any(not isinstance(v, str) or not v.strip() for v in item.values()):
                    raise TextError("항목 제목과 설명이 비어 있습니다.")
                if len(item["title"]) > slot.item_title_max_length or len(item["description"]) > slot.max_length:
                    raise TextError("항목 제목·설명의 최대 길이를 초과했습니다.")
    if numbers(copy) != numbers(page):
        raise TextError("확정 개요의 수치·단위를 보존하고 새로운 수치를 추가하지 않아야 합니다.")


def copy_schema(page: dict, layout: Layout) -> dict:
    properties = {}
    for slot in layout.slots:
        if slot.kind == "text":
            properties[slot.id] = {"type": "string", "minLength": 1, "maxLength": slot.max_length}
        else:
            count = len(page.get("items", []))
            properties[slot.id] = {"type": "array", "minItems": count, "maxItems": count, "items": {
                "type": "object", "required": ["title", "description"], "additionalProperties": False,
                "properties": {
                    "title": {"type": "string", "minLength": 1, "maxLength": slot.item_title_max_length},
                    "description": {"type": "string", "minLength": 1, "maxLength": slot.max_length},
                },
            }}
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}
