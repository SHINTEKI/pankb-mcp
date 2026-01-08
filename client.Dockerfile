FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY ai_client/pyproject.toml ai_client/uv.lock /app/ai_client/

WORKDIR /app/ai_client

RUN uv sync --frozen --no-dev

COPY ai_client/app /app/ai_client/app

WORKDIR /app/ai_client/app

CMD ["uv", "run", "streamlit", "run", "app.py"]