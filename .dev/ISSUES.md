# Issues

## ISSUE-001 — Docker not installed on dev machine
Status: closed
Priority: high
Created: 2026-09-07
Resolved: 2026-09-07

### Problem
PostgreSQL cannot be started locally, so the database-backed path of GET /api/countries has not been verified end-to-end on this machine. docker-compose.yml exists but cannot be run.

### Resolution
PostgreSQL verified running on host machine (port 5432). End-to-end tests for `/health` and `/api/countries` passed successfully using real database.

## ISSUE-002 — pytest suite failing after Milestone 2 changes
Status: closed
Priority: high
Created: 2026-09-07
Resolved: 2026-09-07

### Problem
`pytest` in apps/api failed on all tests. Initially misdiagnosed as a pytest-asyncio / async fixture configuration issue.

### Root cause
`app/schemas/__init__.py` did not export `Observation`; `routes/countries.py` import failed during fixture setup. The pytest-asyncio config was already correct (`asyncio_mode = "auto"`, pytest-asyncio 1.4.0, SQLite async engine + dependency override).

### Resolution
Added the `Observation` export to `app/schemas/__init__.py`. `uv run pytest`: 7 passed, 0 warnings.

## ISSUE-003 — Concurrent ingestion batches duplicated observations
Status: closed
Priority: high
Created: 2026-09-08
Resolved: 2026-09-08

### Problem
Coverage verification found 374 observations where 264 were expected — 110 exact-duplicate rows (same country, source series, period, vintage 1, identical values).

### Root cause
Two batch imports ran concurrently (an orphaned background run plus the sprint batch). Each checked "does a latest observation exist?" before inserting; both saw none and both inserted vintage 1. The application-level skip logic cannot protect against simultaneous writers.

### Resolution
Owner-approved cleanup: duplicate rows deleted, keeping the earliest of each identical pair (dev DB; data fully reproducible via idempotent re-import). Prevention: migration `a1c7e9b04d55` adds `uq_observations_identity` UNIQUE (country_id, source_series_id, period_start, vintage_number), so concurrent runs now fail loudly at the DB instead of silently duplicating.

### Lesson
Never run two ingestion batches at once; uniqueness is now DB-enforced regardless.

## ISSUE-004 — /countries/{iso3}/observations returned cross-country rows
Status: closed
Priority: high
Created: 2026-09-08
Resolved: 2026-09-08

### Problem
Browser verification with all 8 countries loaded showed every /country/[iso3] page rendering identical (CHE) values. The live API returned a mix of rows from several countries for any /countries/{iso3}/observations request. Latent until now: earlier tests and data had only one country with observations.

### Root cause
`list_current_observations` (app/services/observation_service.py) joined the latest-vintage subquery (which was country-scoped) to the outer Observation query only on (source_series_id, period_start, vintage_number). SourceSeries rows are shared across countries — one World Bank series code covers all 8 countries — so the join keys alone matched every country's rows. The outer query and the count query had no country_id filter of their own.

### Resolution
Added `Observation.country_id == country_id` to the outer query and the count query (indicator_id filters already existed in both scopes). Regression suite `tests/test_current_observations_scoping.py` (3 tests, owner-specified cases): USA vs CHE same series/period stay scoped; `?indicator=GDP_GROWTH` returns only that indicator; latest vintage only (superseded value never served); count matches filtered items. Suite: 65 passed. Verified live: USA/CHE/CHN/IND endpoints and pages each return only their own values.
