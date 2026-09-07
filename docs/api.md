# API Reference

Base URL (local): `http://localhost:8000`

## Endpoints

### `GET /`

API identity.

```json
{ "name": "Big Cycle Atlas API", "version": "0.1.0" }
```

### `GET /health`

Liveness + database connectivity. Always returns 200 when the process is up;
`database` reports whether a `SELECT 1` succeeded.

```json
{
  "status": "ok",
  "version": "0.1.0",
  "database": "connected",
  "database_error": null
}
```

`database_error` is populated when `database` is `"unavailable"`.

### `GET /api/countries`

All tracked countries, ordered by name.

```json
[
  {
    "iso3": "CHE",
    "iso2": "CH",
    "name": "Switzerland",
    "region": "Europe",
    "created_at": "2026-09-07T14:03:11.123456+00:00",
    "updated_at": "2026-09-07T14:03:11.123456+00:00"
  }
]
```

### `GET /api/countries/{iso3}`

Single country by ISO3 code (case-insensitive). `404` if not tracked.

## Conventions

- CORS: `GET` methods from origins in `CORS_ORIGINS` (default `http://localhost:3000`).
- Errors follow FastAPI conventions: `{"detail": "..."}`.
- Country identifiers are ISO 3166-1 alpha-3 (`iso3`).
- Future endpoints will be grouped under `/api` and versioned by model, not URL path.

## Planned endpoints (later milestones)

- `GET /api/countries/{iso3}/forces` — 17-force scores
- `GET /api/countries/{iso3}/history` — historical scores
- `GET /api/countries/{iso3}/forecast` — stage-probability windows
- `GET /api/compare?countries=USA,CHN` — comparison sets
- `GET /api/data/sources` — source health and freshness
- Data ingestion endpoints will be admin-only and separate from the public API.