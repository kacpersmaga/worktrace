FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.8 /uv /usr/local/bin/uv

WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/worktrace ./worktrace
COPY data/demo /app/data/demo
RUN uv sync --frozen --no-dev

ENV WORKTRACE_DATA=/app/data WORKTRACE_WORK=/app/work
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "worktrace.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
