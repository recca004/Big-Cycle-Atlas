#!/bin/sh
# Big Cycle Atlas API container entrypoint.
# Idempotent init: wait for Postgres -> alembic upgrade head -> seed ->
# uvicorn. Safe to re-run on every start.
set -eu

echo "[api-init] waiting for database connectivity…"
/app/.venv/bin/python - <<'PY'
import os, sys, time
import psycopg

url = os.environ["DATABASE_URL"].replace("+psycopg", "")
deadline = time.time() + 90
while True:
    try:
        with psycopg.connect(url, connect_timeout=5) as conn:
            conn.execute("SELECT 1")
        print("[api-init] database reachable")
        break
    except Exception as exc:
        if time.time() > deadline:
            print(f"[api-init] database unreachable after 90s: {exc}")
            sys.exit(1)
        time.sleep(2)
PY

echo "[api-init] applying migrations (alembic upgrade head)…"
/app/.venv/bin/alembic upgrade head

echo "[api-init] seeding catalog (countries / sources / indicators)…"
/app/.venv/bin/python -m app.db.seed

echo "[api-init] starting uvicorn on :8000"
exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
