# Big Cycle Atlas — Road to v1.0

Current programme state: **Mission 1 in progress** (2026-03).

## The six missions

| # | Mission | Gate | Status |
|---|---------|------|--------|
| 1 | Complete the 17-force economic engine | 17/17 research modules; max defensible executable forces; momentum for productivity; uncertainty contract; dependency map | **IN PROGRESS** |
| 2 | Big Cycle engine + Research Lab | Experimental composite engine; `/research` live; transition rules researched; experimental isolation | Pending |
| 3 | Complete Astro + Liquid Glass app | Workspace completion (drag/resize/lock), all widgets on real data, component showcase | Pending |
| 4 | Historical validation + forecasting | Release-date discipline, as-of queries, backtest-safety evidence, gated forecast architecture | Pending |
| 5 | Market research + final integration | External review, positioning, integration polish | Pending |
| 6 | QA, self-hosting, v1.0 release prep | Full regression, deployment docs, release checklist | Pending |

## Mission 1 scope (this session)

- [x] Doc corrections (HANDOFF current-state block, this file, FORCE_COMPLETION_MATRIX)
- [x] DEC-042 Option C: productivity own-history % momentum (3y/5y/10y, primary 5y) — shipped
- [ ] Cost competitiveness (REER/relative-ULC research → supported dimension or context module)
- [~] character/participation: DONE (LFP type-B proxy); military: DONE (relative_share type-C); trade/FDI data: DONE. Remaining: cost competitiveness (REER), openness, infrastructure, resource allocation, geography, acts of nature — context modules or delegated proxies still open
- [x] Historical force-scores endpoint: GET /api/countries/{iso3}/forces/{force}/history
- [ ] Methodology states formalised: EXPERIMENTAL / VALIDATED_CANDIDATE / APPROVED_PRODUCTION
- [x] Uncertainty endpoint: GET /api/countries/{iso3}/indicator-uncertainty (4 WGI indicators, CI bounds + source counts)
- [x] Cross-force dependency map: .dev/FORCE_DEPENDENCY_MAP.json (generated from live registries)
- [ ] Progress page reflects real execution state
