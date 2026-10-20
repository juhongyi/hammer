FROM python:3.14.8-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/

ENV UV_PYTHON_DOWNLOADS=never

WORKDIR /workspace

ENV UV_LINK_MODE=copy
CMD ["sh", "-c", "uv sync --locked && exec uv run --locked fastapi dev app/main.py --host 0.0.0.0"]
