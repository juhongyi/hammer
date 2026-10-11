import os
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx2
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import create_app
from app.settings import Settings
from tests.fake_models import ModelFixture


@pytest.fixture
async def api_client():
    database_url = os.environ.get(
        "TEST_DATABASE_URL",
        "postgresql+psycopg://poc:local-poc-password@localhost:55432/presentation",
    )
    schema = f"test_{uuid4().hex}"
    admin_engine = create_async_engine(database_url)
    async with admin_engine.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    scoped_url = make_url(database_url).update_query_dict({"options": f"-csearch_path={schema}"})
    settings = Settings(
        _env_file=None,
        database_url=scoped_url.render_as_string(hide_password=False),
        cloudflare_account_id="test-account",
        cloudflare_api_token="test-token",
        typesafe_api_key="test-key",
    )
    fixture = ModelFixture()
    app = create_app(settings)
    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(application):
        async with original_lifespan(application):
            async with httpx2.AsyncClient(transport=httpx2.MockTransport(fixture.handle)) as models:
                application.state.models.client = models
                yield

    app.router.lifespan_context = lifespan
    try:
        async with app.router.lifespan_context(app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=app), base_url="http://test"
            ) as client:
                yield client, fixture, app
    finally:
        async with admin_engine.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await admin_engine.dispose()
