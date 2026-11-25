# Big Cycle Atlas

A country-level macro cycle tracker built on a measurable Big Cycle framework.

The main question the product answers: **Where are we in the Big Cycle?**

For each supported country, the Atlas collects public economic and
institutional data (World Bank, IMF WEO, BIS, OECD, FRED, WID.world and more)
and measures the 17 Big Cycle forces. All 17 forces are represented through
research modules; published numerical levels currently exist for **9 forces**,
with **2 dimension-only forces** (component scores, no primary level) and
**6 context profiles** (descriptive, not scores). No force is listed as
"deferred" for lack of a score — but unavailability is always labelled, never
substituted. It also provides market regime analysis, strategy research tools,
a portfolio ledger, and a composable workspace of chart and data widgets.

Big Cycle classifications and any composite cycle output are **experimental
research results** — not validated production classifications, and no
forecast probabilities are published (every forecast horizon is gated on
data sufficiency and currently reports unavailable rather than fabricating a
number). No live or simulated data is presented as real beyond its stated
provenance — every value carries source, vintage, and retrieval metadata.

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
- PostgreSQL 14+ — an existing local/network instance (native), or Docker
  (`docker compose -f docker-compose.dev.yml up -d`)
- Optional: Docker Desktop / Compose v2 for the containerised alternative

## Local setup

### Recommended — native Windows launchers

```bat
Setup.bat       :: one-time: deps, .env, migrations, seed
Start-Prod.bat  :: production mode — one process on http://localhost:8000
Start.bat       :: development mode — API :8000 + Astro dev :3000
```

`Setup.bat` and the launchers handle everything below automatically; the
manual steps are for non-Windows setups or troubleshooting.

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

#### Unified terminal data update

`Update.bat` is the single owner-facing command for data refreshes:

```bat
Update.bat                    :: daily macro + market update + Observatory refresh
Update.bat -Full              :: daily update + reference universes + optional WID archive
Update.bat -MacroOnly         :: economic providers only
Update.bat -MarketsOnly       :: financial markets/currencies only
Update.bat -ReferencesOnly    :: reference distributions only
Update.bat -RecalculateOnly   :: recalculate without downloading provider data
Update.bat -Status            :: DB totals, refresh state, lock and schedules
Update.bat -DryRun            :: print the plan without changing data
Update.bat -Help              :: command reference
```

Optional filters: `-Source world_bank|bis|oecd|imf_weo|wid`, `-Country USA`,
`-MarketLookbackDays 30`, and `-WidZip <local archive>`. WID is never
auto-downloaded by the unified updater; pass a locally downloaded ZIP to opt in.
All eight tracked countries are covered by default, immutable observation
vintages are preserved, and provider failures are reported as partial success
(exit `2`) instead of aborting independent sources. Exit `0` means complete
success; exit `1` means a fatal configuration/database/lock failure.

Every run writes a timestamped plain-text log under `.run/updates/` (not
tracked by Git) and uses a shared cross-process update lock. The same lock is
respected by Observatory refresh triggers, so terminal, scheduler, and app
updates cannot overlap. OECD collection uses a rolling request budget with a
55-request/hour safety ceiling plus bounded Retry-After handling.

Scheduled collection is still opt-in: `scripts/ops/install-schedule.ps1`
prints the plan, `-Approve` registers tasks, `-Disable`/`-Enable` toggles them,
and `-Remove` unregisters them. Scheduled data jobs reuse `update.ps1`.

### 3. Frontend (apps/web-astro)

```bash
# from the repo root
npm install
npm run dev      # http://localhost:3000
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

## Deployment — native first

The supported deployment is **native, no containers**. Windows launchers live
at the repo root (`Setup.bat`, `Start.bat`, `Start-Prod.bat`, `Stop.bat`,
`Update.bat`, `Backup.bat`, `Restore.bat`, `Test.bat`, `Status.bat`).

- `Start.bat` (dev): checks deps, PostgreSQL connectivity and config, starts
  the API (:8000) and Astro dev server (:3000), waits for health, opens the
  browser, and refuses duplicate instances. `Stop.bat` stops only the
  processes BCA started.
- `Start-Prod.bat` (prod): a single `serve.py` process on 127.0.0.1:8000
  serves the API **and** the built frontend (`apps/web-astro/dist`) — no dev
  server, no extra web server.
- Scheduled collection via Windows Task Scheduler:
  `scripts/ops/install-schedule.ps1` (dry-run unless `-Approve`).

Linux (Debian/Ubuntu, e.g. Proxmox VM): native systemd deployment —
`deploy/linux/install.sh`, units under `deploy/linux/systemd/`, optional
nginx proxy sample. Full instructions in `docs/DEPLOYMENT.md`.

Docker remains as an **optional** alternative: `docker-compose.yml`
(`--profile scheduled` for the collector), `docker-compose.dev.yml` for a
postgres-only dev database. Nothing requires it.

## Backup & restore

```powershell
Backup.bat                    # pg_dump -Fc into .\backups\
Restore.bat                   # pick a dump, type RESTORE to confirm overwrite
scripts\ops\verify-restore.ps1 -TargetUrl <dsn>   # scratch-DB count check
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
