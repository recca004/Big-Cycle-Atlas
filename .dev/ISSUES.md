# Issues

## ISSUE-001 — Docker not installed on dev machine

Status: open
Priority: high
Created: 2026-09-07

### Problem

PostgreSQL cannot be started locally, so the database-backed path of GET /api/countries has not been verified end-to-end on this machine. docker-compose.yml exists but cannot be run.

### Suspected cause

Docker Desktop not installed on this Windows machine (`docker` command not found).

### Attempts

- Verified tooling: node, npm, python, git available; docker missing.
- Built the full DB layer anyway and covered it with SQLite-backed unit tests (DEC-003) so logic is tested even though the Postgres connection is not.

### Next step

Install Docker Desktop, run `docker compose up -d`, create .env, run the seed script, and hit GET /api/countries to confirm the 8 countries come back from Postgres.