# Big Cycle Atlas — Road to v1.0

Current programme state: **Mission 4 in progress** (2026-11-25). Missions 1–3 delivered; Mission 4 is closing application gaps and has landed the historical-validation foundation.

## The six missions

| # | Mission | Gate | Status |
|---|---------|------|--------|
| 1 | Complete the 17-force economic engine | 17/17 research modules; max defensible executable forces; momentum for productivity; uncertainty contract; dependency map | **COMPLETE** — 9 level-published + 2 dimension-only + 6 context profiles + 0 deferred (17 total); dependency map + force matrix reproducible; uncertainty endpoint + history live |
| 2 | Big Cycle engine + Research Lab | Experimental composite engine; `/research` live; transition rules researched; experimental isolation | **COMPLETE** — registry + 4 composite models + phase/stage classifier + /research UI live, all experimental-gated; retrospective diagnostics manifest generated (4 models × 8 countries) |
| 3 | Complete Astro + Liquid Glass app | Workspace completion (drag/resize/lock), all widgets on real data, component showcase | **MOSTLY COMPLETE** — workspace filters inherited by widgets, pointer drag/resize/lock/undo/redo Playwright-verified, Add to Workspace on key pages, Data Explorer + compare with exports, uncertainty band charts; search/settings/showcase remain (Mission 4 P2) |
| 4 | Historical validation + forecasting | Release-date discipline, as-of queries, backtest-safety evidence, gated forecast architecture | **IN PROGRESS** — execution modes (current/retrospective/strict/assumption) threaded through alignment→normalizer→forces→composites; provider release-evidence matrix; leakage tests; validation API (execution-modes, release-evidence, availability, reference-availability, diagnostics); RL historical-validation section; forecasting scaffolding pending |
| 5 | Market regime research + strategy + paper trading | Market regimes, asset-class analysis, historical strategy research, isolated paper trading, final integration | Pending |
| 6 | QA, self-hosting, v1.0 release prep | Full regression, deployment docs, release checklist | Pending |

## Mission 1 scope (completed)

- [x] Doc corrections (HANDOFF current-state block, this file, FORCE_COMPLETION_MATRIX — now generated reproducibly)
- [x] DEC-042 Option C: productivity own-history % momentum (3y/5y/10y, primary 5y) — shipped
- [x] Cost competitiveness: dimension-only (REER momentum live); level method deferred (DEC-018)
- [x] character/participation: LFP type-B proxy; military: relative_share type-C; trade/FDI data live
- [x] Historical force-scores endpoint: GET /api/countries/{iso3}/forces/{force}/history (now with execution_mode + info_cutoff)
- [x] Methodology states formalised in MethodologyState enum (approved_production / validated_candidate / experimental / context_only)
- [x] Uncertainty endpoints: latest + full history (26 WGI periods) with published CI bounds and source counts
- [x] Cross-force dependency map + project metadata + force matrix — all generated with drift tests
- [x] Progress endpoint reflects real execution state (authoritative /api/research/progress)

## Mission 4 delivered to date (this session)

- Workspace filter inheritance (shared effective-config resolver + unit tests)
- Pointer drag/resize/lock/undo/redo/persist Playwright suite (5 tests)
- Add to Workspace on country/compare/data pages; functional Data Explorer with CSV/JSON export (formula-injection safe)
- Published WGI uncertainty band chart (API history endpoint + widget + mounts)
- Country comparison (multi-country forces + indicators, coverage warnings, exports)
- All three deferred forces → verified context profiles (openness, resource allocation, acts of nature); classifications now 9/2/6/0
- Derived TRADE_OPENNESS_GDP endpoint with component provenance
- Historical execution modes end-to-end + 26 leakage/contract tests
- Provider release-evidence matrix (honest: zero ingested release dates)
- Validation API: /execution-modes, /release-evidence, /countries/{iso3}/availability, /reference-availability, /diagnostics
- Reproducible run manifests on cycle history
- Systematic retrospective diagnostics: 4 models × 8 countries, 2015-2025 (full 2000+ run regenerating)

## Remaining (Mission 4)

- [ ] Historical-validation widget(s) in workspace registry
- [ ] Forecast readiness report (§31) — evidence assessment, no fabricated probabilities
- [ ] Search, settings, component showcase (P2)
- [ ] Browser screenshots + performance/accessibility audit
- [ ] PR #1 update + consolidated acceptance report
