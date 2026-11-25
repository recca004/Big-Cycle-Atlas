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

| `fetchResearchMethods` | `GET /api/research/methods[?state=]` | `MethodInfo[]` |
| `fetchCompositeModels` | `GET /api/research/models` | `CompositeModelInfo[]` (experimental) |
| `fetchCountryCycle` | `GET /api/research/countries/{iso3}/cycle?model=` | `CompositeResult` (experimental) |
| `fetchCycleHistory` | `GET /api/research/countries/{iso3}/cycle/history?model=&start_year=` | `CycleHistoryResponse` (experimental, retrospective) |
| `fetchGeography` | `GET /api/research/countries/{iso3}/geography` | structural profile (static, not a score) |
| `fetchResearchProgress` | `GET /api/research/progress` | `ResearchProgress` |
| `fetchForceHistory` | `GET /api/countries/{iso3}/forces/{force}/history?start_year=` | `ForceHistoryResponse` |

## ResearchProgress (authoritative engine status)

`{as_of_period, total_forces: 17, counts, counts_sum_to_total, forces[]}`. Each force carries a **mutually-exclusive** `primary_classification` (`level_published` | `dimension_only` | `context_profile` | `deferred`) whose counts always sum to 17, plus independent attributes (`approval_state`, `published_dimensions`, `has_context_profile`, `experimental_methods`, `coverage_ceiling`, `live_inputs`).

Types: `src/types/api.ts` + `src/types/research.ts` (must stay aligned with `apps/api/app/schemas/`).
