FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY mcp_server/pyproject.toml mcp_server/uv.lock /app/mcp_server/

WORKDIR /app/mcp_server

RUN uv sync --frozen --no-dev

COPY mcp_server/app /app/mcp_server/app

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
