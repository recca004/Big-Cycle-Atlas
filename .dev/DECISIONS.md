# Decisions

## DEC-001 — npm workspaces as the package manager

Date: 2026-09-07
Status: Accepted

### Decision

Use npm workspaces (root package.json with `workspaces: ["apps/*", "packages/*"]`) rather than pnpm.

### Reason

npm 11 is already installed on the dev machine; pnpm is not. npm workspaces handle the monorepo layout without a global tool install.

### Impact

All frontend npm commands should be run via pnpm. CI (later) must install pnpm.

## DEC-002 — SQLAlchemy 2.0 async with psycopg driver

Date: 2026-09-07
Status: Accepted

### Decision

Backend ORM is SQLAlchemy 2.0 in async mode with the `psycopg` (v3) driver for PostgreSQL.

### Reason

Single mature ORM with typed models; psycopg v3 is the modern Postgres driver with async support.

### Impact

Requires Python 3.10+. Connection string in .env: `DATABASE_URL=postgresql+psycopg://...`.

## DEC-003 — Unit tests run against SQLite via dependency override

Date: 2026-09-07
Status: Accepted

### Decision

pytest runs the API against an in-memory SQLite database by overriding the get_session dependency. Real deployments use PostgreSQL.

### Reason

Allows the test suite to run without Docker/Postgres (Docker unavailable on the current dev machine). Service-layer code is driver-agnostic SQLAlchemy.

### Impact

Postgres-specific features (TimescaleDB, JSONB operators) must not be used in code paths covered only by SQLite tests. Once Docker is available, add an integration test profile against real Postgres.

## DEC-004 — packages/shared holds the canonical country list

Date: 2026-09-07
Status: Accepted

### Decision

The 8 initial countries (USA, CHN, CHE, DEU, FRA, GBR, JPN, IND) are defined once in packages/shared and consumed by both the backend seed script and the frontend.

### Reason

Single source of truth prevents drift between backend seed data and frontend display lists.

### Impact

Adding a country means editing packages/shared first, then re-seeding.

## DEC-005 — Frontend fetches countries client-side via NEXT_PUBLIC_API_URL

Date: 2026-09-07
Status: Accepted

### Decision

The /countries page fetches from the FastAPI backend in a client component using the NEXT_PUBLIC_API_URL environment variable. No Next.js rewrites/proxy yet.

### Reason

Simplest correct wiring for Milestone 1; avoids server-side fetch complexity before there is real data.

### Impact

API must be running for /countries to show data; the page shows an explicit error state when the API is unreachable. Server-side fetching can replace this later.