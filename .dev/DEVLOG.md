# Devlog

## 2026-09-07 15:00 — Milestone 1: Foundation

### Goal

Build the complete foundation (Milestone 1): monorepo, FastAPI backend, Next.js frontend, Postgres docker service, initial 8 countries, .dev handoff system, docs, README.

### Completed

- Monorepo structure: apps/web, apps/api, packages/shared, scripts, data, docs, .dev
- FastAPI backend: /health, /api/countries, countries model + seed script, pytest suite
- Next.js frontend: home page + /countries page with API client, Conceptzilla design system styling
- docker-compose.yml (Postgres 16), .env.example, README, docs (architecture, data-model, methodology, api)
- All .dev handoff files created

### Changed

- .dev/* (all files)
- apps/api/* (new)
- apps/web/* (new)
- packages/shared/* (new)
- scripts/* (new)
- docker-compose.yml, .env.example, README.md, .gitignore, docs/*

### Tests

- pytest (apps/api): 4 passed — health endpoint, countries list, country detail by ISO3, root
- pnpm build (apps/web): succeeded

### Issues

- Docker not installed on dev machine → Postgres container and DB-backed endpoint not verified end-to-end (ISSUE-001). Tests use SQLite override (DEC-003).

### Next

- Owner installs Docker → verify DB path end-to-end, then approve Milestone 2 (data model + indicator system).