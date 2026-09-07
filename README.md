# Big Cycle Atlas

A country-level macro cycle tracker built on a measurable Big Cycle framework.

The main question the product answers: **Where are we in the Big Cycle?**

For each supported country, the Atlas will collect public economic and institutional
data, score 17 forces (0–100), determine the country's current phase and stage,
track changes over time, and later support forecasting, market regime analysis,
backtesting, and paper trading.

No live or simulated data is presented as real. The project is in early development.

## Status

Milestone 1 (Foundation) is complete: FastAPI backend, Next.js frontend, PostgreSQL
schema, and the initial 8-country set. See `.dev/PROJECT_STATUS.md` for details.

Initial countries: United States (USA), China (CHN), Switzerland (CHE), Germany
(DEU), France (FRA), United Kingdom (GBR), Japan (JPN), India (IND).

## Tech stack

- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS, Apache ECharts (later)
- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic
- **Database:** PostgreSQL (Docker Compose)
- **Tooling:** uv, npm workspaces, pytest, Ruff

## Requirements

- Node.js 20+
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- Docker Desktop (for PostgreSQL) — or any reachable PostgreSQL instance

## Local setup

### 1. Database

```bash
docker compose up -d
```

This starts PostgreSQL 16 on `localhost:5432` with user/password `postgres`/`postgres`
and database `bigcycleatlas`.

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

- `/` — global dashboard placeholder ("Where are we in the Big Cycle?")
- `/countries` — country list, fetched live from the API

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