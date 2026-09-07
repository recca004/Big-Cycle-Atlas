# Architecture

## Overview

Big Cycle Atlas is a monorepo with a Next.js frontend and a FastAPI backend, both
backed by PostgreSQL. The long-term direction is a data pipeline:

```
RAW → NORMALIZED → FEATURE → FORCE SCORE → CYCLE SCORE → FORECAST
```

Raw external observations are never overwritten. Each layer is stored separately so
debugging and historical backtesting remain possible.

```
┌─────────────┐     HTTP      ┌──────────────┐    SQL    ┌────────────┐
│  Next.js    │ ───────────▶ │   FastAPI    │ ────────▶ │ PostgreSQL │
│  apps/web   │               │   apps/api   │           │ (Docker)   │
└─────────────┘               └──────┬───────┘           └────────────┘
                                     │
                              data_sources/ adapters (M3+)
                              World Bank, BIS, OECD, FRED, ...
```

## Components

### Frontend — `apps/web`

- Next.js App Router, TypeScript, Tailwind CSS v4.
- `lib/api.ts` is the single API client module (reads `NEXT_PUBLIC_API_URL`).
- `types/` mirrors the API's Pydantic schemas.
- Design system: Conceptzilla (see `design.md`, gitignored — editorial, near-black
  on off-white, large tightly-tracked headlines).
- Apache ECharts will be added with the historical charts milestone.

### Backend — `apps/api`

Layered:

- `api/routes/` — HTTP layer only (validation, status codes, no business logic)
- `services/` — business logic, all DB access via injected `AsyncSession`
- `models/` — SQLAlchemy ORM models
- `schemas/` — Pydantic response models
- `core/` — settings (pydantic-settings, env validation)
- `db/` — engine/session management + seed script
- `data_sources/` — source adapters (Milestone 3+), each returning the common
  internal observation format
- `scoring/` — force score calculation (Milestone 5+)
- `forecasting/` — phase probability models (Milestone 8+)

Rules:

- Python calculations produce all numeric scores. An LLM may later *explain*
  calculated values, never create them.
- Every scoring result stores its model version.

### Shared — `packages/shared`

TypeScript types and the canonical initial-country list
(`data/initial-countries.json`). The backend seed script reads the same JSON file,
making it the single source of truth for the tracked country set (DEC-004).

### Database — PostgreSQL (Docker)

Docker Compose service `postgres` (PostgreSQL 16). TimescaleDB may be added later
if observation-volume queries need it. The layered data model is documented in
[data-model.md](data-model.md).

## Key decisions

See `.dev/DECISIONS.md` for the decision log. Highlights:

- npm workspaces for the monorepo (DEC-001)
- SQLAlchemy 2.0 async + psycopg 3 (DEC-002)
- Unit tests run against SQLite via dependency override (DEC-003)

## Windows dev note

psycopg async requires a selector-based asyncio event loop. The documented dev
command is `uv run python run.py` from `apps/api`, which sets
`WindowsSelectorEventLoopPolicy` before uvicorn starts. Running
`uvicorn app.main:app` directly on Windows will hit the Proactor loop and fail
DB calls.

## Deployment

Not yet configured. When it is: exclude `.dev/`, `docs/` internal drafts, and any
fixture data from deployment output. `.dev` stays in Git but never ships.