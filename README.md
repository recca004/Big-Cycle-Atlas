# Big Cycle Atlas

A country-level macro cycle tracker built on a measurable Big Cycle framework.

The main question the product answers: **Where are we in the Big Cycle?**

For each supported country, the Atlas will collect public economic and institutional
data, score 17 forces (0–100), determine the country's current phase and stage,
track changes over time, and later support forecasting, market regime analysis,
backtesting, and paper trading.

No live or simulated data is presented as real. The project is in early development.

## Status

Milestone 5 (indicator normalization + first executable force layer) is complete;
Sprint 6.12 done. Live dev state: 6,814 observations, 27 indicators, 22 source
series, 10 data sources, 1,872 indicator diagnostics, 8 countries, 660 backend
tests passing, `normalization-v0.8` / `force-aggregation-v0.3`. 5/17 forces have
executable scores (all computed in-memory; no force-score API yet). See
`.dev/PROJECT_STATUS.md` for details.

Initial countries: United States (USA), China (CHN), Switzerland (CHE), Germany
(DEU), France (FRA), United Kingdom (GBR), Japan (JPN), India (IND).

## Tech stack

- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS v4 — an Astro
  migration is in progress under `apps/web-astro` (see `feature/big-cycle-atlas-astro-v2`)
- **Backend:** Python, FastAPI, SQLAlchemy 2.0 (async), psycopg 3, Pydantic
- **Database:** PostgreSQL (any reachable instance; docker-compose provided)
- **Tooling:** uv, npm workspaces, pytest, Ruff

## Requirements

- Node.js 20+
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 14+ — via Docker Desktop (`docker compose up -d`) or an existing
  local/network instance

## Local setup

### 1. Database

Option A — Docker Compose:

```bash
docker compose up -d
```

This starts PostgreSQL 16 on `localhost:5432` with user/password `postgres`/`postgres`
and database `bigcycleatlas`.

Option B — an existing PostgreSQL instance (what the primary dev machine uses):
point `DATABASE_URL` in `apps/api/.env` at it. Example (host PostgreSQL 18):

```
DATABASE_URL=postgresql+psycopg://<user>:<password>@localhost:5432/<database>
```

Set it once — `.env` must not contain multiple `DATABASE_URL` lines (the last
one silently wins).

### 2. Backend (apps/api)

```bash
cd apps/api
uv sync
# On Windows, set the DATABASE_URL in apps/api/.env first (see .env.example)
uv run python -m app.db.seed     # creates tables + seeds the 8 countries
uv run python run.py            # starts the API on http://localhost:8000
```

Notes:

- On Windows, always start the server with `uv run python run.py` (not
  `uvicorn app.main:app` directly). The entrypoint sets the selector event loop
  that psycopg requires; uvicorn would otherwise default to the Proactor loop.
- `GET /health` reports API status and database connectivity.
- `GET /api/countries` returns the database-backed country list.

### 3. Frontend (apps/web)

```bash
# from the repo root
npm install
npm run dev
```

Opens on http://localhost:3000.

- `/` — global dashboard with tracked-country cards
- `/countries` — country list with data coverage, fetched live from the API
- `/country/{iso3}` — per-country data: economic, trade, governance, inequality,
  military, debt & credit, and productivity sections
- `/country/{iso3}/forces` — 17-force coverage statuses (scores not yet exposed)

Set `NEXT_PUBLIC_API_URL` in `apps/web/.env.local` if the API is not on
http://localhost:8000 (see `.env.example`).

### 4. Tests

```bash
# backend
cd apps/api
uv run pytest

# frontend typecheck + production build
cd ../..
npm run build
```

## Repository layout

```
apps/
  web/        Next.js frontend
  api/        FastAPI backend
packages/
  shared/     Shared TypeScript types + canonical country data
scripts/      Ingest / calculate / maintenance scripts (later)
data/         Fixtures and mappings
docs/         Architecture, methodology, data model, API docs
.dev/         Development handoff system (not part of the product)
```

## Development handoff system

The `.dev/` folder tracks project state between development sessions:
`HANDOFF.md`, `PROJECT_STATUS.md`, `DEVLOG.md`, `DECISIONS.md`, `ISSUES.md`,
`BACKLOG.md`, `DATA_SOURCES.md`. Read `HANDOFF.md` first when resuming work.
It is committed to Git but is not part of the shipped product.

## License

All rights reserved.