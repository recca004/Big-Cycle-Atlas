# Deployment — native first

Big Cycle Atlas runs natively on Windows (primary) and Debian/Ubuntu.
Docker exists as an **optional** alternative (`docker-compose.yml`) — it is
not required, not prioritised, and the app is fully functional without it.
Do not migrate the existing host PostgreSQL database into Docker.

## Architecture

- **API + web are one process.** `apps/api/serve.py` runs uvicorn; when
  `apps/web-astro/dist` exists it serves the built frontend at `/` same-origin
  (`BCA_WEB_DIST` overrides the path; unset it to run API-only).
- Dev mode runs two processes: `run.py` (API :8000, reload) + Astro dev :3000.
- The browser calls `/api/...` relative to its origin in production builds;
  `PUBLIC_API_URL` overrides for split deployments.
- Defaults bind to `127.0.0.1`. The app has **no authentication** — keep it
  loopback-only, or expose it privately behind your own authenticated
  reverse proxy (nginx sample in `deploy/linux/nginx-bca.conf`).

## Windows (primary)

Requirements: Node.js 20+, Python 3.11+, uv, PostgreSQL 14+ (the existing
host install and `bigcycleatlas_dev` database are reused — all observations,
market data and portfolio records are preserved).

Launchers (repo root — double-click or run from a terminal):

| Launcher | What it does |
|---|---|
| `Setup.bat` | deps check, `uv sync`, `npm install`, `.env` bootstrap, `alembic upgrade head`, seed |
| `Start.bat` | dev mode: checks deps + PostgreSQL + config, starts API (:8000) and Astro (:3000), waits for health, opens browser; refuses duplicate instances |
| `Start-Prod.bat` | production mode: single process on :8000 serving API + built frontend (needs `dist/`; run `Update.bat` first) |
| `Stop.bat` | stops only the process trees recorded in `.run\*.pid` — verifies each PID belongs to this repo first |
| `Update.bat` | `git pull`, `uv sync`, `npm install`, `alembic upgrade head`, rebuild |
| `Backup.bat` / `Restore.bat` | `pg_dump -Fc` into `.\backups\`; restore requires typing `RESTORE` to confirm the overwrite |
| `Test.bat` | backend pytest + astro check + vitest (`-E2E` adds Playwright) |
| `Status.bat` | pid liveness + HTTP health |

pg_dump must be on PATH or `PG_BIN` set (e.g. `C:\Program Files\PostgreSQL\18\bin`).

### Scheduled jobs (Windows)

`scripts\ops\install-schedule.ps1` registers daily Task Scheduler jobs —
market update 06:30, macro snapshot 06:00, backup 02:00, health check 12:00 —
with overlap prevention (`IgnoreNew`). It is a **dry run** unless run with
`-Approve`; use `-Remove` to unregister. WID bulk ingest stays a manual
opt-in (`collect_snapshot.py --wid-zip`).

## Linux (Debian/Ubuntu, e.g. a Proxmox VM)

`deploy/linux/install.sh` installs packages, creates the `bca` user +
`bigcycleatlas` database, syncs deps, builds the frontend, and installs the
systemd units:

- `bca-api.service` — `serve.py` on 127.0.0.1:8000 (hardened: NoNewPrivileges,
  ProtectSystem, PrivateTmp).
- `bca-snapshot.timer`, `bca-market-update.timer`, `bca-backup.timer` —
  daily one-shot jobs (Type=oneshot prevents overlap). **Disabled by
  default**; enable explicitly after review.

Cron alternative: equivalent `@daily` lines running the same commands.
Reverse proxy: `deploy/linux/nginx-bca.conf` sample (or Caddy) for
private-network exposure — terminate authentication upstream.

**Status: instructions written, not verified on a live Linux host.**

## Docker (optional)

`docker-compose.yml` still provides the containerised stack
(`--profile scheduled` adds the collector). `docker-compose.dev.yml` is
postgres-only for local dev. Use it if convenient; nothing depends on it.
