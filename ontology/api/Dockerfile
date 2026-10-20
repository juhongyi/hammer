FROM python:3.14.8-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/

ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy

WORKDIR /workspace

CMD ["sh", "-ec", "uv sync --locked && exec uv run --locked uvicorn app.main:app --host 0.0.0.0 --reload"]
