"""Test-only server: deterministic model fixtures with real Chromium rendering."""
from contextlib import asynccontextmanager

from app.main import app, lifespan
from app.pipeline import Pipeline
from test_pipeline import FakeModels


@asynccontextmanager
async def test_lifespan(application):
    async with lifespan(application):
        application.state.pipeline = Pipeline(application.state.store, FakeModels())
        yield


app.router.lifespan_context = test_lifespan
