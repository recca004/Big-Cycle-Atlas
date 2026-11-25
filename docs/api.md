# API Reference

Base URL (local): `http://localhost:8000`

All endpoints are read-only (`GET`). CORS accepts `GET` from origins listed in
`CORS_ORIGINS` (default `http://localhost:3000`). Errors follow FastAPI
conventions: `{"detail": "..."}`. Country identifiers are ISO 3166-1 alpha-3
(`iso3`), case-insensitive.

## Endpoints

### `GET /`

API identity.

```json
{ "name": "Big Cycle Atlas API", "version": "0.1.0" }
```

### `GET /health`

Liveness + database connectivity. Always returns 200 when the process is up;
`database` reports whether a `SELECT 1` succeeded. `database_error` is populated
when `database` is `"unavailable"`.

```json
{
  "status": "ok",
  "version": "0.1.0",
  "database": "connected",
  "database_error": null
}
```

### `GET /api/countries`

All tracked countries, ordered by name. Each entry carries latest-vintage
coverage fields: `observation_count`, `indicator_count`,
`latest_observation_year`.

```json
[
  {
    "iso3": "CHE",
    "iso2": "CH",
    "name": "Switzerland",
    "region": "Europe",
    "observation_count": 850,
    "indicator_count": 22,
    "latest_observation_year": 2025,
    "created_at": "2026-09-07T14:03:11.123456+00:00",
    "updated_at": "2026-09-07T14:03:11.123456+00:00"
  }
]
```

### `GET /api/countries/{iso3}`

Single country by ISO3 code. `404` if not tracked.

### `GET /api/countries/{iso3}/observations`

Latest-vintage raw observations for a country, newest first. Paginated.

Query parameters:

- `indicator` — canonical indicator code filter (e.g. `GDP_GROWTH`)
- `limit` — page size (max 1000, default 100)
- `offset` — pagination offset

```json
{
  "items": [
    {
      "id": 123,
      "indicator_code": "GDP_GROWTH",
      "value": 1.3,
      "period_start": "2025-01-01T00:00:00Z",
      "retrieved_at": "2026-09-08T10:00:00Z",
      "vintage_number": 1,
      "unit": "annual %",
      "source_key": "world_bank"
    }
  ],
  "total": 11,
  "limit": 100,
  "offset": 0
}
```

Only the latest vintage of each observation is served; superseded values are
never returned.

### `GET /api/countries/{iso3}/force-coverage`

Per-force data-coverage status for all 17 forces. Statuses only — this endpoint
deliberately returns **no scores**.

```json
{
  "country": "USA",
  "forces": [
    {
      "code": "rule_of_law",
      "name": "Rule of law",
      "description": "...",
      "status": "available",
      "coverage_notes": "...",
      "live_inputs": [
        {
          "indicator_code": "RULE_OF_LAW_WGI_SCORE",
          "name": "...",
          "has_data": true,
          "has_source_series": true,
          "source": "world_bank",
          "latest_period": "2024-01-01T00:00:00Z"
        }
      ],
      "candidate_inputs": []
    }
  ]
}
```

`status` is one of `available` | `partial` | `defined_not_sourced` | `missing`.
A `partial` ceiling marks forces whose inputs are proxy-only (DEC-009).

### `GET /api/data/sources`

Registered data sources (World Bank, BIS, OECD, IMF WEO, WID, …) with status
(`planned` | `testing` | `active` | `broken`).

### `GET /api/data/ingestion-runs`

Recent ingestion runs: source, indicator, status, observation counts, errors.

### `GET /api/indicators`

The canonical indicator catalog (27 entries).

### `GET /api/indicators/{code}/revisions`

Revision history for an indicator — each provider correction creates a new
immutable observation vintage plus an `IndicatorRevision` row.

## Conventions

- Endpoints are grouped under `/api` and versioned by model, not URL path.
- Raw observations are immutable; corrections arrive as new vintages.
- MISSING data is never returned as zero and never forward-filled.

## Planned endpoints (later milestones)

- `GET /api/countries/{iso3}/force-scores` — approved force dimensions only
- `GET /api/countries/{iso3}/history` — historical scores
- `GET /api/countries/{iso3}/forecast` — stage-probability windows
- `GET /api/compare?countries=USA,CHN` — comparison sets
- Data ingestion endpoints will be admin-only and separate from the public API.
