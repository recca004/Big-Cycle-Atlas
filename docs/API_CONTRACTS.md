# API Contracts (consumed by web-astro)

Base: `API_URL` (default `http://localhost:8000`). All endpoints read-only from the frontend's perspective. See `docs/api.md` for the authoritative list; this file documents the typed client in `src/lib/api/client.ts`.

| Client fn | Endpoint | Returns |
|---|---|---|
| `fetchHealth` | `GET /api/health` | `{status}` |
| `fetchCountries` | `GET /api/countries/` | `Country[]` |
| `fetchCountry` | `GET /api/countries/{iso3}` | `Country \| null` |
| `fetchCountryObservations` | `GET /api/countries/{iso3}/observations?indicator&limit&offset` | `ObservationPage` |
| `fetchForceCoverage` | `GET /api/countries/{iso3}/force-coverage` | `ForceCoverageData` |
| `fetchForceScores` | `GET /api/countries/{iso3}/force-scores[?period=YYYY-Qn]` | `ForceScoresResponse` |
| `fetchDataSources` | `GET /api/data/sources` | `DataSource[]` |
| `fetchIngestionRuns` | `GET /api/data/ingestion-runs` | `IngestionRun[]` |
| `fetchIndicators` | `GET /api/indicators/` | `Indicator[]` |
| `fetchIndicatorRevisions` | `GET /api/indicators/{code}/revisions` | `IndicatorRevision[]` |

## ForceScoresResponse

`{iso3, period, forces: ForceScore[]}` where `ForceScore` carries `force_code`, `level_score` (0–100 or `null` when deferred), `status`, `reasons`, `limitations`, `model_version`, `force_aggregation_version`. Deferred is never zero — always `null` + reasons.

Types: `src/types/api.ts` (must stay aligned with `apps/api/app/schemas/`).
