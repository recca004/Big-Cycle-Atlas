# Big Cycle Atlas API — production image.
# Reproducible build: pinned base image + uv.lock dependency resolution.
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

# uv for locked dependency installs
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /usr/local/bin/

WORKDIR /app

# Dependency layer (cached while uv.lock unchanged)
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Application
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini run.py ./
COPY scripts ./scripts

# Canonical country/indicator seed file (normally resolved relative to the
# repo; containers get it at a fixed path).
COPY docker-seed/initial-countries.json /app/docker-seed/initial-countries.json
ENV BCA_SEED_FILE=/app/docker-seed/initial-countries.json

# Non-root runtime user
RUN useradd --create-home --uid 10001 bca && chown -R bca:bca /app
USER bca

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
