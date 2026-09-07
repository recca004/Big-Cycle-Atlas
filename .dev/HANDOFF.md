# Big Cycle Atlas — Development Handoff

Last updated: 2026-09-07
Current version: 0.1.0
Current branch: main

## Current state

Milestone 1 (Foundation) built: FastAPI backend, Next.js frontend, PostgreSQL schema and docker-compose, initial 8 countries seed, home page + country list page reading from the API. Backend tests pass; database-backed run not yet verified on this machine (Docker not installed — see Known issues).

## Completed

- Monorepo structure (apps/web, apps/api, packages/shared, scripts, data, docs, .dev)
- FastAPI app with /health and /api/countries endpoints
- SQLAlchemy 2.0 async models + Pydantic schemas
- Countries table + seed script for 8 initial countries
- Next.js (App Router, TypeScript, Tailwind) frontend
- Home page ("Where Are We in the Big Cycle?") and /countries page
- Frontend API client with NEXT_PUBLIC_API_URL env var
- docker-compose.yml for PostgreSQL 16
- pytest suite for health endpoint and country service
- README with local setup instructions

## In progress

- None (Milestone 1 complete, awaiting approval)

## Next task

1. Verify database-backed /api/countries end-to-end once Docker is available
2. Milestone 2: data model + indicator system (observations, indicators, data_sources tables)

## Current architecture

Monorepo. `apps/api` is FastAPI + SQLAlchemy async + Pydantic, layering api/ → services/ → db/. `apps/web` is Next.js App Router with a typed API client in lib/. `packages/shared` holds shared country constants (single source of truth for ISO3 codes). PostgreSQL via docker-compose.

## Running locally

Frontend:
npm run dev (in apps/web) — or `npm run dev -w apps/web` from root

Backend:
uvicorn app.main:app --reload (in apps/api, with .venv active)

Database:
docker compose up -d (from repo root)

## Current routes

- / — global dashboard placeholder (headline + phase summary intro)
- /countries — country list from API

## API endpoints

- GET /health
- GET /api/countries

## Data sources connected

- None yet

## Data sources pending

- World Bank (Milestone 3)
- BIS, OECD, FRED, Eurostat, ECB, SNB, UN Comtrade (Milestone 4)

## Database status

Schema defined (countries table) with seed script ready. Postgres container configured but not runnable on the dev machine yet (no Docker). Backend and frontend run and pass tests without the DB.

## Cycle model status

Not built. Phase/stage enum and 17-force definitions documented in docs/data-model.md, shared constants in packages/shared. No scoring logic yet.

## Known issues

- Docker is not installed on this dev machine, so the PostgreSQL container and DB-backed endpoint have not been run end-to-end here. docker compose config is ready; needs verification on a Docker-capable machine.
- design.md is gitignored by owner request (kept local only).

## Files changed in latest session

- .dev/* (all handoff files)
- apps/api/* (entire backend)
- apps/web/* (entire frontend)
- packages/shared/*
- docker-compose.yml, .env.example, README.md, .gitignore
- docs/architecture.md, docs/data-model.md, docs/methodology.md, docs/api.md

## Important decisions

- DEC-001: npm workspaces chosen as package manager (pnpm not installed)
- DEC-002: SQLAlchemy 2.0 async + psycopg (not asyncpg) for Postgres
- DEC-003: SQLite used for unit tests via dependency override; Postgres for real runs
- DEC-004: packages/shared is the source of truth for the 8 initial countries

## Questions / decisions needed from project owner

- Install Docker Desktop (or provide a remote Postgres) so the database path can be verified end-to-end.
- Font choice: design.md specifies Suisse Intl (commercial). The frontend currently uses a system font stack. Should we license Suisse Intl or pick a free alternative (e.g. Inter, Neue Haas Grotesk substitute)?

## Recommended next action

Install Docker Desktop, run `docker compose up -d`, then seed and verify GET /api/countries returns the 8 countries from the database. Then approve Milestone 2 (data model + indicator system).