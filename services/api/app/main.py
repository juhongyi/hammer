from contextlib import asynccontextmanager
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, Response

from .ontology import validate_ontology
from .pipeline import Pipeline
from .render import font_path, slide_html
from .schemas import Confirmation, Input, Ontology, Outline
from .store import Store
from .validation import nonblank, structure, validate_outline

load_dotenv()


@asynccontextmanager
async def lifespan(app):
    app.state.store = Store()
    app.state.pipeline = Pipeline(app.state.store)
    yield


app = FastAPI(title="Presentation PoC", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/font")
def font():
    if not font_path().is_file():
        return Response(status_code=404)
    return FileResponse(font_path(), media_type="font/ttf", headers={"Cache-Control": "public, max-age=86400"})


@app.get("/runs")
def list_runs():
    return app.state.store.list()


@app.get("/runs/{id_}")
def get_run(id_: str):
    run = app.state.store.get(id_)
    if run is None:
        raise HTTPException(404, "실행을 찾을 수 없습니다.")
    return run


@app.post("/runs", status_code=202)
def create_run(body: Input, background: BackgroundTasks):
    if not body.text.strip():
        raise HTTPException(422, "텍스트를 입력하세요.")
    run = dict(id=str(uuid4()), text=body.text, status="outline_pending", stage="개요 생성 시작",
               error=None, outline=None, confirmed_outline=None, trace=[], slides=[])
    app.state.store.save(run)
    background.add_task(app.state.pipeline.outline, run)
    return {"id": run["id"]}


@app.post("/runs/{id_}/confirm", status_code=202)
def confirm(id_: str, body: Confirmation, background: BackgroundTasks):
    run = get_run(id_)
    if run["status"] != "outline_ready":
        raise HTTPException(409, "개요 편집·확정 대기 상태가 아닙니다.")
    try:
        validate_outline(body.outline, run["total_pages"], run["chapter_count"])
        if structure(body.outline) != structure(Outline.model_validate(run["outline"])):
            raise ValueError("페이지 순서·챕터 구성은 변경할 수 없습니다.")
        run = app.state.store.claim(id_, body.outline.model_dump(), app.state.store.ontology())
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    background.add_task(app.state.pipeline.slides, run)
    return {"id": id_}


@app.get("/ontology")
def ontology():
    return app.state.store.ontology()


@app.post("/ontology/validate")
def check_ontology(body: Ontology):
    try:
        nonblank(body.model_dump())
        validate_ontology(body)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"valid": True}


@app.put("/ontology")
def save_ontology(body: Ontology):
    check_ontology(body)
    app.state.store.save_ontology(body.model_dump())
    return {"valid": True}


@app.get("/runs/{id_}/slides/{index}", response_class=HTMLResponse)
def render_slide(id_: str, index: int):
    run = get_run(id_)
    if run["status"] != "completed":
        raise HTTPException(409, "모든 페이지의 검사 통과 후에 결과를 열람할 수 있습니다.")
    if not 0 <= index < len(run["slides"]):
        raise HTTPException(404, "페이지를 찾을 수 없습니다.")
    return HTMLResponse(slide_html(run["slides"][index], index + 1), headers={"Cache-Control": "no-store"})
