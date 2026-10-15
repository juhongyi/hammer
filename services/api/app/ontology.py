from .schemas import Layout, Ontology, Slot


def initial_ontology() -> Ontology:
    definitions = [
        ("cover", "발표 제목과 주제를 소개하는 표지", "발표의 첫 페이지", "본문 설명"),
        ("message", "하나의 중심 주장이나 핵심 통찰 강조", "단일 핵심 메시지", "여러 독립 항목이나 비교"),
        ("list", "독립적인 항목을 나열", "병렬적인 특징·근거·목록", "시간 순서나 명시적인 양측 비교"),
        ("comparison", "두 대상을 동일 관점에서 비교", "실제로 개요에 존재하는 두 비교 대상", "단순히 항목이 두 개인 목록"),
        ("process", "순서나 시간에 따른 단계 표현", "선후 관계가 있는 단계", "순서가 없는 독립 항목"),
        ("closing", "발표의 결론·요약·다음 행동 전달", "마지막 페이지의 결론이나 요청", "새로운 본문 논점"),
    ]
    layouts = []
    for id_, purpose, _, _ in definitions:
        slots = [Slot(id="title", role="페이지 제목", kind="text", required=True, max_length=64)]
        if id_ != "cover":
            slots += [
                Slot(id="message", role="페이지 핵심 메시지", kind="text", required=True, max_length=140),
                Slot(id="items", role="개요 항목을 순서대로 표현. 제목과 설명을 모두 보존", kind="items",
                     required=False, max_length=180, min_items=2 if id_ in ("comparison", "process") else 0,
                     max_items=2 if id_ == "comparison" else 3 if id_ == "message" else 6),
            ]
        layouts.append(Layout(id=id_, purpose=purpose, supported_types=[id_], enabled=True, slots=slots))
    return Ontology(types=[dict(id=i, purpose=p, suitable=s, unsuitable=u) for i, p, s, u in definitions], layouts=layouts)


def validate_ontology(value: Ontology) -> None:
    original = initial_ontology()
    if [t.id for t in value.types] != [t.id for t in original.types]:
        raise ValueError("기존 표현 유형의 ID와 순서를 유지해야 합니다.")
    if [l.id for l in value.layouts] != [l.id for l in original.layouts]:
        raise ValueError("기존 레이아웃 6종의 ID와 순서를 유지해야 합니다.")
    for layout, base in zip(value.layouts, original.layouts):
        if len(layout.supported_types) != len(set(layout.supported_types)):
            raise ValueError("지원 유형이 중복되었습니다.")
        known = {t.id for t in value.types}
        if not set(layout.supported_types) <= known:
            raise ValueError("알 수 없는 지원 유형입니다.")
        if (layout.id == "cover" and layout.supported_types != ["cover"]) or (
            layout.id != "cover" and "cover" in layout.supported_types
        ):
            raise ValueError("표지와 본문 레이아웃의 관계를 유지해야 합니다.")
        if [s.id for s in layout.slots] != [s.id for s in base.slots]:
            raise ValueError("기존 슬롯 ID와 순서를 유지해야 합니다.")
        for slot, limit in zip(layout.slots, base.slots):
            if slot.kind != limit.kind or slot.required != limit.required:
                raise ValueError("슬롯 형태와 필수 여부를 유지해야 합니다.")
            if slot.max_length > limit.max_length or slot.item_title_max_length > limit.item_title_max_length:
                raise ValueError("고정 레이아웃의 최대 텍스트 용량을 초과했습니다.")
            if not limit.min_items <= slot.min_items <= slot.max_items <= limit.max_items:
                raise ValueError("항목 수 제약이 고정 레이아웃의 표현 범위를 벗어났습니다.")


def candidates(ontology: Ontology, type_id: str, page: dict) -> list[Layout]:
    result = []
    for layout in ontology.layouts:
        if not layout.enabled or type_id not in layout.supported_types:
            continue
        if (page["id"] == "cover") != (layout.id == "cover"):
            continue
        if any(slot.required and not page.get(slot.id) for slot in layout.slots):
            continue
        if any(slot.kind == "items" and not slot.min_items <= len(page.get(slot.id, [])) <= slot.max_items
               for slot in layout.slots):
            continue
        result.append(layout)
    return result
