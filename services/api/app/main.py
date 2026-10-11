import asyncio
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx2
from fastapi import FastAPI, HTTPException, Request
from sqlalchemy import update
from sqlmodel import SQLModel, select

from .catalogue import candidates, initial_catalogue
from .db import CatalogueRow, PresentationRow, make_engine, session_for
from .generation import OUTLINE_INSTRUCTION, generate_presentation
from .providers import ModelError, Models
from .schemas import (
    Catalogue,
    Outline,
    PresentationSummary,
    PresentationView,
    RenderValidation,
    TextInput,
)
from .settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    engine = make_engine(config)
    tasks: set[asyncio.Task] = set()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with engine.begin() as connection:
            await connection.run_sync(SQLModel.metadata.create_all)
        async with session_for(engine) as session:
            if await session.get(CatalogueRow, 1) is None:
                session.add(CatalogueRow(document=initial_catalogue().model_dump()))
            interrupted = await session.exec(
                select(PresentationRow).where(PresentationRow.status.in_(["queued", "generating"]))
            )
            for row in interrupted:
                row.status, row.phase = "failed", "생성 중단"
                row.error = "서버 재시작으로 생성이 중단되었습니다. 개요는 보존되었습니다."
                session.add(row)
            await session.commit()
        async with httpx2.AsyncClient(timeout=config.model_timeout_seconds) as client:
            app.state.models = Models(config, client)
            app.state.engine = engine
            yield
            for task in list(tasks):
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
        await engine.dispose()

    app = FastAPI(title="System One Presentation PoC", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        async with session_for(engine) as session:
            await session.exec(select(CatalogueRow))
        return {"status": "ok"}

    @app.get("/api/ontology", response_model=Catalogue)
    async def get_catalogue():
        async with session_for(engine) as session:
            row = await session.get(CatalogueRow, 1)
            return row.document

    @app.put("/api/ontology", response_model=Catalogue)
    async def save_catalogue(document: Catalogue):
        updated = document.model_copy(update={"version": document.version + 1})
        async with session_for(engine) as session:
            result = await session.exec(
                update(CatalogueRow)
                .where(CatalogueRow.id == 1, CatalogueRow.version == document.version)
                .values(document=updated.model_dump(), version=updated.version)
            )
            if result.rowcount != 1:
                raise HTTPException(
                    409, "다른 수정이 먼저 저장되었습니다. 최신 데이터를 다시 불러오세요."
                )
            await session.commit()
        return updated

    @app.get("/api/presentations", response_model=list[PresentationSummary])
    async def list_presentations():
        async with session_for(engine) as session:
            rows = await session.exec(
                select(PresentationRow).order_by(PresentationRow.created_at.desc())
            )
            return [
                PresentationSummary(
                    id=row.id,
                    title=row.outline["pages"][0]["title"],
                    status=row.status,
                    page_count=row.page_count,
                    created_at=row.created_at,
                )
                for row in rows
            ]

    @app.post("/api/presentations", response_model=PresentationView, status_code=201)
    async def create_outline(body: TextInput, request: Request):
        try:
            outline = await request.app.state.models.generate(
                OUTLINE_INSTRUCTION, {"text": body.text}, Outline, 14000
            )
        except ModelError as exc:
            raise HTTPException(502, str(exc)) from exc
        row = PresentationRow(
            source=body.text, outline=outline.model_dump(), page_count=len(outline.pages)
        )
        async with session_for(engine) as session:
            session.add(row)
            await session.commit()
        return view(row)

    @app.get("/api/presentations/{presentation_id}", response_model=PresentationView)
    async def get_presentation(presentation_id: str):
        async with session_for(engine) as session:
            return view(await get_row(session, presentation_id))

    @app.put("/api/presentations/{presentation_id}/outline", response_model=PresentationView)
    async def save_outline(presentation_id: str, outline: Outline):
        async with session_for(engine) as session:
            row = await get_row(session, presentation_id, lock=True)
            if row.status not in {"outline_ready", "failed"}:
                raise HTTPException(409, "생성 중이거나 완료된 개요는 변경할 수 없습니다.")
            if len(outline.pages) != row.page_count:
                raise HTTPException(422, "자동 결정된 장수를 유지해야 합니다.")
            row.outline = outline.model_dump()
            row.status, row.phase, row.error = "outline_ready", "개요를 확정해 주세요.", None
            session.add(row)
            await session.commit()
            return view(row)

    @app.post("/api/presentations/{presentation_id}/generate", response_model=PresentationView)
    async def start_generation(presentation_id: str, request: Request):
        models = request.app.state.models
        try:
            models.require_llm()
            models.require_jev()
        except ModelError as exc:
            raise HTTPException(503, str(exc)) from exc
        async with session_for(engine) as session:
            row = await get_row(session, presentation_id, lock=True)
            if row.status not in {"outline_ready", "failed"}:
                raise HTTPException(409, "이미 생성 중이거나 완료된 발표자료입니다.")
            catalogue_row = await session.get(CatalogueRow, 1)
            catalogue = Catalogue.model_validate(catalogue_row.document)
            if not any(layout.enabled for layout in catalogue.layouts):
                raise HTTPException(422, "사용 가능한 디자인이 없습니다. 개요는 보존되었습니다.")
            row.snapshot = catalogue.model_dump()
            row.status, row.phase, row.error = "queued", "생성 대기 중", None
            row.run_id, row.slides = str(uuid4()), []
            session.add(row)
            await session.commit()
            result = view(row)
        task = asyncio.create_task(
            generate_presentation(engine, models, presentation_id, result.run_id)
        )
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return result

    @app.post("/api/presentations/{presentation_id}/validation", response_model=PresentationView)
    async def validate_render(presentation_id: str, report: RenderValidation):
        async with session_for(engine) as session:
            row = await get_row(session, presentation_id, lock=True)
            if row.run_id != report.run_id:
                raise HTTPException(409, "이전 생성 작업의 배치 검사 결과입니다.")
            if row.status != "awaiting_validation":
                raise HTTPException(409, "배치 검사를 기다리는 작업이 아닙니다.")
            current = view(row)
            if len(current.slides) != row.page_count or [
                slide.index for slide in current.slides
            ] != list(range(row.page_count)):
                raise HTTPException(422, "확정 장수와 순서가 유지되지 않았습니다.")
            if sorted(page.index for page in report.pages) != list(range(row.page_count)):
                raise HTTPException(422, "모든 페이지를 한 번씩 검사해야 합니다.")
            issues = [
                f"{page.index + 1}페이지: {issue}" for page in report.pages for issue in page.issues
            ]
            if not report.font_loaded:
                issues.append("한국어 폰트 로딩에 실패했습니다.")
            for slide in current.slides:
                available = candidates(
                    slide.content, slide.trace.classification.choice, current.snapshot
                )
                if slide.layout.id not in {layout.id for layout in available}:
                    issues.append(f"{slide.index + 1}페이지: 저장된 디자인 제약 위반")
            row.status = "failed" if issues else "completed"
            row.error = " / ".join(issues) if issues else None
            row.phase = "배치 검사 실패" if issues else "전체 슬라이드 생성·배치 검사 완료"
            session.add(row)
            await session.commit()
            return view(row)

    return app


async def get_row(session, presentation_id: str, lock: bool = False) -> PresentationRow:
    statement = select(PresentationRow).where(PresentationRow.id == presentation_id)
    if lock:
        statement = statement.with_for_update()
    row = (await session.exec(statement)).one_or_none()
    if row is None:
        raise HTTPException(404, "발표자료를 찾을 수 없습니다.")
    return row


def view(row: PresentationRow) -> PresentationView:
    return PresentationView(
        id=row.id,
        source=row.source,
        outline=row.outline,
        status=row.status,
        phase=row.phase,
        error=row.error,
        run_id=row.run_id,
        slides=row.slides,
        snapshot=row.snapshot,
        created_at=row.created_at,
    )


app = create_app()
