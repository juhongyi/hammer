FROM python:3.14.8-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.13.1 /uv /uvx /usr/local/bin/

ENV UV_PYTHON_DOWNLOADS=never

WORKDIR /workspace

CMD ["sleep", "infinity"]
