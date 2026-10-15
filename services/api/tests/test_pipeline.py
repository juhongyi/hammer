import asyncio
from copy import deepcopy

import pytest

from app.models import ModelError, TextError
from app.ontology import initial_ontology
from app.pipeline import Pipeline
from app.render import Renderer
from app.store import Store


def draft():
    return {"cover": {"id": "cover", "title": "한국어 발표"}, "pages": [
        {"id": f"p{i}", "title": "계획", "message": "고객 만족을 높입니다.",
         "items": [{"title": "현황", "description": "만족도 20% 개선을 목표로 합니다."}]} for i in range(1, 6)]}


class FakeModels:
    def __init__(self, reject_outline=0, copy_failures=0, error_at=None, invalid_draft=0, count=6, chapters=2):
        self.reject_outline = reject_outline
        self.copy_failures = copy_failures
        self.error_at = error_at
        self.invalid_draft = invalid_draft
        self.count = count
        self.chapters = chapters
        self.calls = []
        self.text_calls = []

    async def choice(self, state, instructions, criteria):
        self.calls.append((instructions, state, criteria))
        if self.error_at and self.error_at in instructions:
            raise ModelError("모델 API 호출 실패 (HTTP 429).")
        if "총 장수" in instructions:
            selected = str(self.count)
        elif "챕터 수" in instructions:
            selected = str(self.chapters)
        elif "마지막 본문" in instructions:
            selected = "2" if "2" in criteria else next(iter(criteria))
        elif "개요 의미 검수" in instructions and self.reject_outline:
            self.reject_outline -= 1
            selected = "fail"
        elif "pass" in criteria:
            selected = "pass"
        elif "표현 유형" in instructions:
            selected = "cover" if state["page"]["id"] == "cover" else "list"
        else:
            selected = next(iter(criteria))
        return {"type": "choice", "choice": selected, "confidence": 1,
                "probabilities": {id_: int(id_ == selected) for id_ in criteria}, "model": "test-only"}

    async def text(self, task, context, shape, feedback="", schema=None):
        self.text_calls.append((context, feedback))
        if "request" in context:
            value = draft()
            value["pages"] = [{**deepcopy(value["pages"][0]), "id": f"p{i}"} for i in range(1, self.count)]
            if self.invalid_draft:
                self.invalid_draft -= 1
                value["pages"].pop()
            return value
        if "draft" in context:
            return {"titles": ["챕터 제목"] * self.chapters}
        page = context["page"]
        value = {id_: deepcopy(page[id_]) for id_ in shape}
        if self.copy_failures and page["id"] == "p1":
            self.copy_failures -= 1
            value["items"][0]["description"] = "만족도 30% 개선"
        return value


class FakeRenderer:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass

    async def check(self, slide):
        pass


def setup(tmp_path, **kwargs):
    store = Store(str(tmp_path / "test.sqlite3"))
    models = FakeModels(**kwargs)
    pipeline = Pipeline(store, models, FakeRenderer)
    run = dict(id="test", text="고객 만족도 개선 계획", status="outline_pending", stage="시작",
               error=None, outline=None, confirmed_outline=None, trace=[], slides=[])
    store.save(run)
    return store, models, pipeline, run


def confirm(store, run):
    outline = deepcopy(store.get(run["id"])["outline"])
    outline["pages"][0]["message"] = "사용자가 확정한 중요 내용"
    return store.claim(run["id"], outline, store.ontology())


def test_full_pipeline_preserves_edits_order_and_real_rendering(tmp_path):
    store, models, pipeline, run = setup(tmp_path)
    asyncio.run(pipeline.outline(run))
    assert run["status"] == "outline_ready"
    assert run["chapter_groups"] == [["p1", "p2"], ["p3", "p4", "p5"]]
    claimed = confirm(store, run)
    pipeline.renderer_factory = Renderer
    asyncio.run(pipeline.slides(claimed))
    result = store.get("test")
    assert result["status"] == "completed", result["error"]
    assert [s["page_id"] for s in result["slides"]] == ["cover", "p1", "p2", "p3", "p4", "p5"]
    assert result["slides"][1]["copy"]["message"] == "사용자가 확정한 중요 내용"
    assert sum(t["stage"] == "구조·수치·의미·배치 검사 통과" for t in result["trace"]) == 6
    assert any("레이아웃 선택" in call[0] for call in models.calls)


def test_outline_retry_keeps_counts_and_boundaries(tmp_path):
    store, models, pipeline, run = setup(tmp_path, reject_outline=1)
    asyncio.run(pipeline.outline(run))
    assert run["status"] == "outline_ready"
    assert sum("총 장수" in c[0] for c in models.calls) == 1
    assert sum("챕터 수" in c[0] for c in models.calls) == 1
    assert sum("마지막 본문" in c[0] for c in models.calls) == 1
    calls = [c for c in models.text_calls if "request" in c[0]]
    assert len(calls) == 2
    assert calls[1][0]["chapter_groups"] == run["chapter_groups"]
    assert calls[1][1]


@pytest.mark.parametrize("count,chapters", [(6, 1), (6, 5), (30, 1), (30, 29), (30, 3)])
def test_chapter_boundary_extremes_are_contiguous_nonempty_and_complete(tmp_path, count, chapters):
    _, models, pipeline, run = setup(tmp_path, count=count, chapters=chapters)
    asyncio.run(pipeline.outline(run))
    assert run["status"] == "outline_ready", run["error"]
    assert len(run["chapter_groups"]) == chapters
    assert all(run["chapter_groups"])
    assert [id_ for group in run["chapter_groups"] for id_ in group] == [f"p{i}" for i in range(1, count)]
    assert sum("마지막 본문" in c[0] for c in models.calls) == chapters - 1


@pytest.mark.parametrize("invalid_draft,expected", [(1, "outline_ready"), (2, "failed")])
def test_structural_outline_failure_retries_once(tmp_path, invalid_draft, expected):
    _, models, pipeline, run = setup(tmp_path, invalid_draft=invalid_draft)
    asyncio.run(pipeline.outline(run))
    assert run["status"] == expected
    assert len([c for c in models.text_calls if "request" in c[0]]) == 2


@pytest.mark.parametrize("failures,expected", [(1, "completed"), (2, "failed")])
def test_copy_failure_retries_only_failed_page_and_preserves_selection(tmp_path, failures, expected):
    store, models, pipeline, run = setup(tmp_path, copy_failures=failures)
    asyncio.run(pipeline.outline(run))
    claimed = confirm(store, run)
    asyncio.run(pipeline.slides(claimed))
    assert claimed["status"] == expected
    page_calls = [c for c in models.text_calls if c[0].get("page", {}).get("id") == "p1"]
    assert len(page_calls) == 2
    assert page_calls[0][0] == page_calls[1][0]
    assert sum("p1 표현 유형" in c[0] for c in models.calls) == 1
    assert sum("p1 레이아웃" in c[0] for c in models.calls) == 1
    assert claimed["confirmed_outline"]["pages"][0]["message"] == "사용자가 확정한 중요 내용"
    if expected == "failed":
        assert len(claimed["slides"]) == 1


def test_model_error_does_not_regenerate(tmp_path):
    _, models, pipeline, run = setup(tmp_path, error_at="개요 의미 검수")
    asyncio.run(pipeline.outline(run))
    assert run["status"] == "failed"
    assert "429" in run["error"]
    assert sum("request" in c[0] for c in models.text_calls) == 1
    assert not any(t.get("regenerate") for t in run["trace"])


def test_text_model_transport_error_does_not_regenerate(tmp_path):
    _, models, pipeline, run = setup(tmp_path)
    async def fail(*args, **kwargs):
        models.text_calls.append(args)
        raise ModelError("연결 실패")
    models.text = fail
    asyncio.run(pipeline.outline(run))
    assert run["status"] == "failed"
    assert len(models.text_calls) == 1


def test_empty_candidates_fail_and_ontology_is_snapshotted(tmp_path):
    store, models, pipeline, run = setup(tmp_path)
    asyncio.run(pipeline.outline(run))
    ontology = store.ontology()
    next(l for l in ontology["layouts"] if l["id"] == "list")["enabled"] = False
    store.save_ontology(ontology)
    claimed = confirm(store, run)
    store.save_ontology(initial_ontology().model_dump())
    asyncio.run(pipeline.slides(claimed))
    assert claimed["status"] == "failed"
    assert "후보가 없습니다" in claimed["error"]
    assert not any("p1 레이아웃 선택" in c[0] for c in models.calls)
    assert not next(l for l in claimed["ontology"]["layouts"] if l["id"] == "list")["enabled"]


def test_layout_check_failure_triggers_one_page_retry(tmp_path):
    store, models, pipeline, run = setup(tmp_path)
    class RejectOnce(FakeRenderer):
        rejected = False
        async def check(self, slide):
            if not self.rejected:
                self.rejected = True
                raise TextError("배치 실패: 텍스트 잘림")
    pipeline.renderer_factory = RejectOnce
    asyncio.run(pipeline.outline(run))
    claimed = confirm(store, run)
    asyncio.run(pipeline.slides(claimed))
    assert claimed["status"] == "completed"
    assert sum(c[0].get("page", {}).get("id") == "cover" for c in models.text_calls) == 2


def test_completed_results_survive_ontology_edit(tmp_path):
    store, _, pipeline, run = setup(tmp_path)
    asyncio.run(pipeline.outline(run))
    claimed = confirm(store, run)
    asyncio.run(pipeline.slides(claimed))
    before = store.get("test")
    changed = store.ontology()
    changed["types"][2]["purpose"] = "수정한 목록 유형 목적"
    changed["layouts"][2]["enabled"] = False
    store.save_ontology(changed)
    assert store.get("test") == before


def test_restart_marks_inflight_failed_and_preserves_confirmation(tmp_path):
    store, _, pipeline, run = setup(tmp_path)
    asyncio.run(pipeline.outline(run))
    claimed = confirm(store, run)
    reloaded = Store(store.path).get("test")
    assert reloaded["status"] == "failed"
    assert reloaded["confirmed_outline"] == claimed["confirmed_outline"]
