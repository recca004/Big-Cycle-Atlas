# Big Cycle Atlas

A country-level macro cycle tracker built on a measurable Big Cycle framework.

The main question the product answers: **Where are we in the Big Cycle?**

For each supported country, the Atlas collects public economic and institutional
data (World Bank, IMF WEO, BIS, OECD, FRED, WID.world and more), scores 17
forces (0–100), places the country in a phase/stage of the long-term debt and
internal-order cycle, and tracks changes over time. It also provides market
regime analysis, strategy research tools, a portfolio ledger, and a composable
workspace of chart and data widgets.

No live or simulated data is presented as real beyond its stated provenance —
every value carries source, vintage, and retrieval metadata.

## Status

v1.0.0-rc.1. Live dev state: 17,141 observations, 87,872 market observations,
7,976 reference observations, 33 indicators, 10 data sources, 8 countries,
967 ingestion runs. Backend: ~800 tests. Frontend: vitest + Playwright suites
including an accessibility audit.

Initial countries: United States (USA), China (CHN), Switzerland (CHE), Germany
(DEU), France (FRA), United Kingdom (GBR), Japan (JPN), India (IND).

## Tech stack

- **Frontend:** Astro + React islands, TypeScript, Tailwind CSS v4, ECharts
- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), psycopg 3, Pydantic
- **Database:** PostgreSQL 14+ (16 in Docker)
- **Tooling:** uv, npm workspaces, pytest, Ruff, Playwright, vitest

## Requirements

- Node.js 20+
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- PostgreSQL 14+ — via Docker (`docker compose -f docker-compose.dev.yml up -d`)
  or an existing local/network instance
- For the full container deployment: Docker Desktop / Docker Engine + Compose v2

## Local setup

### 1. Database

Option A — dev compose (PostgreSQL only):

```bash
docker compose -f docker-compose.dev.yml up -d
```

Option B — an existing PostgreSQL instance: point `DATABASE_URL` in
`apps/api/.env` at it (see `apps/api/.env.example`). Set it once — `.env` must
not contain multiple `DATABASE_URL` lines (the last one silently wins).

### 2. Backend (apps/api)

```bash
cd apps/api
uv sync
uv run alembic upgrade head      # schema migrations
uv run python -m app.db.seed     # seeds countries, indicators, sources
uv run python run.py             # API on http://localhost:8000
```

Notes:

- On Windows, always start the server with `uv run python run.py` (not
  `uvicorn app.main:app` directly): the entrypoint sets the selector event
  loop that psycopg requires.
- `GET /health` reports API status and database connectivity.
- Data ingestion is a separate step — see `apps/api/scripts/` (e.g.
  `collect_snapshot.py`, `ingest_markets.py`).

### 3. Frontend (apps/web-astro)

```bash
# from the repo root
npm install
npm run dev      # http://localhost:4321
```

The dev server proxies `/api` to `http://localhost:8000`. Set
`PUBLIC_API_URL` if the API lives elsewhere.

Key surfaces: global dashboard, per-country pages (data + forces), markets,
strategies, research lab, portfolio, and a composable workspace. Press
**Ctrl/Cmd+K** anywhere for global search. Preferences (theme, transparency,
motion, default country/currency) live under Settings and persist versioned
in localStorage.

### 4. Tests

```bash
cd apps/api && uv run pytest          # backend suite
npm run test                           # frontend vitest
npm run test:e2e                       # Playwright (needs dev servers)
npm run check                          # astro check (0 errors)
npm run build                          # production build
```

## Production deployment (Docker Compose)

```bash
cp .env.example .env          # set POSTGRES_PASSWORD
docker compose up -d --build  # web on http://localhost:8080
```

- Single exposed port (`WEB_PORT`, default 8080), bound to loopback by
  default. For LAN exposure set `BIND_ADDR=0.0.0.0` and put your own
  authenticated reverse proxy in front — the app has no built-in auth.
- The API container runs `alembic upgrade head` + idempotent seed on start.
- Scheduled collection: `docker compose --profile scheduled up -d` adds a
  collector that runs a daily macro snapshot (06:00 Europe/Zurich) and an
  incremental market update.

## Backup & restore

```powershell
scripts\ops\backup.ps1            # pg_dump -Fc into .\backups\
scripts\ops\restore.ps1 <file>    # restore (refuses to run against dev DB)
scripts\ops\verify-restore.ps1    # restore into scratch DB + count check
```

`pg_dump` must be on PATH or `PG_BIN` set (e.g.
`C:\Program Files\PostgreSQL\18\bin`). Backups are gitignored.

## Repository layout

```
apps/
  web-astro/  Astro + React frontend (the shipped UI)
  api/        FastAPI backend, ingestion scripts, alembic migrations
packages/
  shared/     Shared TypeScript types + canonical country data
scripts/
  ingest/     Data ingestion entry points
  ops/        Backup / restore / dev / setup scripts (ps1 + sh)
data/         Fixtures and mappings
docs/         Architecture, methodology, data model, API docs
.dev/         Development handoff system (not part of the product)
```

## Security & limitations

- No authentication or multi-user support — designed for local or
  single-operator deployment. Do not expose the API publicly.
- No built-in rate limiting beyond source-API politeness.
- Docker deployment files are provided and statically reviewed; verify
  `docker compose up -d --build` on your own host before relying on it.
- WID.world data requires a manually downloaded bulk ZIP (opt-in).

## Development handoff system

The `.dev/` folder tracks project state between development sessions:
`HANDOFF.md`, `PROJECT_STATUS.md`, `DEVLOG.md`, `DECISIONS.md`, `ISSUES.md`,
`BACKLOG.md`, `DATA_SOURCES.md`, plus per-mission acceptance reports. Read
`HANDOFF.md` first when resuming work. Committed to Git, not part of the
shipped product.

## License

Proprietary / private project.
