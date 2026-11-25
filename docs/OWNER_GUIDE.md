# Owner guide — daily use

## Daily research

Double-click **`Start.bat`** (dev: live-reload UI on :3000) or
**`Start-Prod.bat`** (prod: single process on :8000 — recommended for daily
use). It checks everything, waits for health, and opens the browser.
**`Stop.bat`** shuts down only Big Cycle Atlas processes.
**`Status.bat`** shows what's running.

## Updating data (observations, not code)

**`Update.bat`** — refreshes data only, never touches code:
macro/economic snapshot (all sources, revision-tracked) + incremental
market update, then prints DB counts. `-SkipMarkets` skips the market leg.
WID.world stays manual: `collect_snapshot.py --wid-zip <path>`.

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

**Enable:** `powershell -File scripts\ops\install-schedule.ps1` prints the
plan (dry run); `-Approve` registers the tasks.
**Disable:** `... -Remove` unregisters all four, or disable individually in
`taskschd.msc` → Task Scheduler Library (prefix `BCA-`).
Jobs: snapshot 06:00, market update 06:30, backup 02:00, health 12:00 —
overlap-guarded. Nothing schedules itself without your approval.

## Updating the app (code, not data)

**`Upgrade.bat`** — application code upgrade with safety gates:
checks the branch, refuses uncommitted changes, takes a pre-migration
backup (required — `-SkipBackup` only if you know why), `git pull
--ff-only` (never resets), `uv sync`, `npm install`,
`alembic upgrade head` (failures reported, DB left untouched), frontend
rebuild. Re-run any time; failures stop before damage.

## Exporting workspaces and preferences

Workspaces, layouts and preferences live in your browser's localStorage —
export them from the Workspace page ("Export workspace JSON") and re-import
on another machine. Settings → Local data can reset prefs or workspaces.

## Preserving data across upgrades

All data lives in the PostgreSQL `bigcycleatlas_dev` database (plus
`backups\`). Updates never drop or recreate it — `Update.bat` only runs
`alembic upgrade head`, which applies migrations forward and preserves
all observations, market data, and paper portfolio records. Before any
risky upgrade: run `Backup.bat` first.
