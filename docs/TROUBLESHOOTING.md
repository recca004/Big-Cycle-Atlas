# Troubleshooting

| Symptom | Fix |
|---|---|
| `Missing tools: uv` on Setup | Install uv (`irm astral.sh/uv.ps1 | iex`), then re-run Setup.bat |
| `Cannot connect to PostgreSQL` | Check `apps/api/.env` `DATABASE_URL`; verify PostgreSQL service is running; test with `psql <dsn>` |
| `apps/api/.env has multiple DATABASE_URL` | Keep exactly one `DATABASE_URL=` line — last silently wins otherwise |
| `Port 8000 already in use` | Another process holds the port. `Status.bat` shows BCA state; find the owner via `Get-NetTCPConnection -LocalPort 8000` |
| `already running (pid file)` but nothing runs | `Stop.bat` cleans stale `.run\*.pid` files automatically |
| API starts but health fails | Check `apps/api/.env`; on Windows the server must start via `run.py`/`serve.py` (selector event loop) — never bare `uvicorn` |
| `Production build missing` | Run `Update.bat` or `npm run build` |
| `pg_dump`/`pg_restore` not found | Set `PG_BIN` to the PostgreSQL bin dir or add it to PATH |
| Restore refuses the dev database | By design — restore into a scratch DB (`verify-restore.ps1`) |
| `Psycopg cannot use ProactorEventLoop` | The app was started bypassing `run.py`/`serve.py` — always use the launchers or those entrypoints |
| Browser opens but page is blank in dev | Wait a few seconds (Vite cold start), or check `Status.bat` |

Logs: API output goes to the hidden process — restart in a visible console
with `cd apps/api && .venv\Scripts\python serve.py` for debugging.
