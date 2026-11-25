# Owner guide — daily use

## Daily research

Double-click **`Start.bat`** (dev: live-reload UI on :3000) or
**`Start-Prod.bat`** (prod: single process on :8000 — recommended for daily
use). It checks everything, waits for health, and opens the browser.
**`Stop.bat`** shuts down only Big Cycle Atlas processes.
**`Status.bat`** shows what's running.

## Updating data

- Macro/economic snapshot (all sources, revision-tracked):
  `cd apps/api && uv run python scripts/collect_snapshot.py`
- Market data (incremental):
  `uv run python scripts/ingest_markets.py --start <YYYY-MM-DD>`
- WID.world: manual bulk ZIP only: `collect_snapshot.py --wid-zip <path>`
- Health of the data: `Status.bat` → `GET /health`, and
  `uv run python scripts/print_db_counts.py`

## Backups

**`Backup.bat`** → timestamped `pg_dump -Fc` into `.\backups\` (30 kept).
`pg_dump` must be on PATH or set `PG_BIN` (e.g.
`C:\Program Files\PostgreSQL\18\bin`).

## Restoring safely

**`Restore.bat`** lists recent dumps, shows the target DB, and requires
typing `RESTORE` before overwriting anything. To verify a backup without
risking the dev DB, restore into a scratch database instead:

```powershell
psql -c "CREATE DATABASE bca_verify" -U postgres
scripts\ops\verify-restore.ps1 -File backups\<file>.dump -TargetUrl postgresql://.../bca_verify
```

## Optional scheduled tasks

`powershell -File scripts\ops\install-schedule.ps1` prints the plan (dry
run). Register with `-Approve`; remove with `-Remove`. Jobs: snapshot
06:00, market update 06:30, backup 02:00, health check 12:00 daily —
overlap-guarded. Nothing schedules itself without your approval.

## Updating the app

**`Update.bat`** = `git pull` → `uv sync` → `npm install` →
`alembic upgrade head` → frontend rebuild. Safe to re-run.

## Preserving data across upgrades

All data lives in the PostgreSQL `bigcycleatlas_dev` database (plus
`backups\`). Updates never drop or recreate it — `Update.bat` only runs
`alembic upgrade head`, which applies migrations forward and preserves
all observations, market data, and paper portfolio records. Before any
risky upgrade: run `Backup.bat` first.
