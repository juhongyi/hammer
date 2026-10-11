from .schemas import CAPACITIES, Catalogue, Layout, SlideContent

TYPES = [
    (
        "introduction",
        "도입",
        "발표 전체의 주제·구성·목적을 안내하는 소개 페이지. "
        "구체적인 주장·목표·핵심 수치를 전달하는 것이 주된 경우는 강조로 구분한다.",
    ),
    (
        "emphasis",
        "강조",
        "하나의 주장·목표·핵심 수치를 중심 메시지로 전달하는 페이지. "
        "구체적인 달성 목표를 강조하는 내용도 포함하며 발표 전체를 안내하는 도입과 구분한다.",
    ),
    ("enumeration", "나열", "여러 항목을 동등한 수준에서 전달한다."),
    ("comparison", "비교", "대상 간 차이, 장단점 또는 대안을 비교한다."),
    ("process", "순서·과정", "단계, 진행 순서 또는 시간 흐름을 전달한다."),
    ("closing", "요약·행동 제안", "결론을 요약하거나 다음 행동을 제안한다."),
]
LAYOUTS = [
    ("cover", "표지", "큰 제목으로 발표의 주제와 목적을 소개한다.", ["introduction"]),
    (
        "message",
        "핵심 메시지",
        "중심 주장을 크게 강조하고 근거를 덧붙인다.",
        ["emphasis", "closing"],
    ),
    (
        "list",
        "목록",
        "동등한 항목, 비교 대상, 요약 항목을 카드로 정리한다.",
        ["enumeration", "comparison", "closing"],
    ),
    ("comparison", "비교", "두 대상의 차이를 좌우의 동일한 슬롯으로 비교한다.", ["comparison"]),
    (
        "process",
        "과정",
        "입력 순서를 유지해 단계 또는 항목을 순서대로 전달한다.",
        ["process", "enumeration"],
    ),
    ("closing", "마무리", "결론과 후속 행동을 명확히 전달한다.", ["closing", "emphasis"]),
]


def initial_catalogue() -> Catalogue:
    layouts = []
    for layout_id, name, purpose, supports in LAYOUTS:
        minimum, maximum, text_max = CAPACITIES[layout_id]
        layouts.append(
            {
                "id": layout_id,
                "name": name,
                "purpose": purpose,
                "supports": supports,
                "enabled": True,
                "slots": {
                    "title": {"role": "title", "description": "페이지의 제목", "max_chars": 48},
                    "key_message": {
                        "role": "key_message",
                        "description": "페이지의 중심 주장",
                        "max_chars": 96,
                    },
                    "body": {
                        "description": "소제목과 설명문의 묶음. 순서와 의미를 유지해 배치한다.",
                        "min_items": minimum,
                        "max_items": maximum,
                        "heading_max_chars": 32,
                        "text_max_chars": text_max,
                    },
                },
            }
        )
    return Catalogue.model_validate(
        {
            "version": 1,
            "types": [
                {"id": key, "name": name, "description": description}
                for key, name, description in TYPES
            ],
            "layouts": layouts,
        }
    )


def fits(content: SlideContent, layout: Layout) -> bool:
    slots = layout.slots
    return (
        len(content.title) <= slots.title.max_chars
        and len(content.key_message) <= slots.key_message.max_chars
        and slots.body.min_items <= len(content.blocks) <= slots.body.max_items
        and all(
            len(block.heading) <= slots.body.heading_max_chars
            and len(block.text) <= slots.body.text_max_chars
            for block in content.blocks
        )
    )


def candidates(content: SlideContent, type_id: str, catalogue: Catalogue) -> list[Layout]:
    return sorted(
        [
            layout
            for layout in catalogue.layouts
            if layout.enabled and type_id in layout.supports and fits(content, layout)
        ],
        key=lambda item: item.id,
    )
