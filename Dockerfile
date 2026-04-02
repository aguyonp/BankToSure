FROM python:3.11-slim-trixie

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen

RUN uv run playwright install-deps chromium \
    && uv run playwright install chromium \
    && rm -rf /var/lib/apt/lists/*

COPY . .

ENTRYPOINT ["uv", "run", "python", "main.py"]
CMD ["--schedule"]