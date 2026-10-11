"""HTTP-level model fixtures used only by tests, never by the production application."""

import json

import httpx2

from app.catalogue import TYPES


class ModelFixture:
    def __init__(self):
        self.requests: list[dict] = []
        self.fail = False
        self.unfaithful = False

    def outline(self, count: int = 6):
        return {
            "pages": [
                {
                    "title": TYPES[index % 6][1],
                    "key_message": f"{TYPES[index % 6][1]}의 핵심 메시지입니다.",
                    "main_content": "확정된 내용과 수치를 유지합니다.",
                }
                for index in range(count)
            ]
        }

    def handle(self, request: httpx2.Request):
        payload = json.loads(request.content)
        self.requests.append({"url": str(request.url), "payload": payload})
        if self.fail:
            return httpx2.Response(529, json={"detail": "test provider failure"})
        if request.url.host == "api.cloudflare.com":
            data = json.loads(payload["messages"][1]["content"])
            if "page" not in data:
                count = 30 if data["text"] == "test:30" else 6
                output = self.outline(count)
                if data["text"] == "test:max":
                    for page in output["pages"]:
                        page["main_content"] = "test:max"
            else:
                page = data["page"]
                index = data["page_index"] % 6
                count = [1, 2, 6, 2, 5, 2][index]
                output = {
                    "title": page["title"],
                    "key_message": page["key_message"],
                    "blocks": [
                        {"heading": "주요 내용", "text": page["main_content"][:80]}
                        for number in range(count)
                    ],
                }
                if page["main_content"] == "test:max":
                    output = {
                        "title": page["title"] + "가" * (48 - len(page["title"])),
                        "key_message": "가" * 96,
                        "blocks": [
                            {
                                "heading": "가" * 32,
                                "text": "가" * [120, 160, 100, 180, 80, 120][index],
                            }
                            for _ in range(count)
                        ],
                    }
            return httpx2.Response(
                200,
                json={
                    "success": True,
                    "result": {"response": json.dumps(output, ensure_ascii=False)},
                },
            )
        assert request.url.host == "api.typesafe.ai"
        criteria = payload["questions"]["decision"]["criteria"]
        if "faithful" in criteria:
            choice = "unfaithful" if self.unfaithful else "faithful"
        elif "content" in payload["state"]:
            type_id = payload["state"]["expression_type"]["id"]
            preferred = {
                "introduction": "cover",
                "emphasis": "message",
                "enumeration": "list",
                "comparison": "comparison",
                "process": "process",
                "closing": "closing",
            }[type_id]
            choice = preferred if preferred in criteria else next(iter(criteria))
        else:
            choice = next(
                (key for key, name, _ in TYPES if payload["state"]["title"].startswith(name)),
                "emphasis",
            )
        remaining = len(criteria) - 1
        probabilities = {
            key: (0.8 if key == choice else 0.2 / remaining) if remaining else 1.0
            for key in criteria
        }
        return httpx2.Response(
            200,
            json={
                "model": "jev-1.13.0",
                "usage": {"input_tokens": 50, "output_tokens": 0},
                "answers": {
                    "decision": {
                        "type": "choice",
                        "choice": choice,
                        "confidence": 0.8,
                        "probabilities": probabilities,
                    }
                },
            },
        )
