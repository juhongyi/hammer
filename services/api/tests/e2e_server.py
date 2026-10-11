"""Test-only ASGI entrypoint. Mounted exclusively by compose.test.yaml."""

from contextlib import asynccontextmanager

import httpx2

from app.main import create_app
from app.settings import Settings
from tests.fake_models import ModelFixture

fixture = ModelFixture()
app = create_app(
    Settings(
        cloudflare_account_id="test-account",
        cloudflare_api_token="test-token",
        typesafe_api_key="test-key",
    )
)
original_lifespan = app.router.lifespan_context


@asynccontextmanager
async def lifespan(application):
    async with original_lifespan(application):
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(fixture.handle)) as client:
            application.state.models.client = client
            yield


app.router.lifespan_context = lifespan


@app.post("/test/provider-failure/{enabled}")
async def failure(enabled: bool):
    fixture.fail = enabled
    return {"failure": enabled}
