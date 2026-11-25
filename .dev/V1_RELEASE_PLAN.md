# Big Cycle Atlas — Road to v1.0

Current programme state: **Mission 5 delivered** (2026-11-25). Missions 1–5 delivered; Mission 6 (QA, self-hosting, v1.0 release prep) is next. Acceptance report: .dev/MISSION5_ACCEPTANCE.md.

## The six missions

| # | Mission | Gate | Status |
|---|---------|------|--------|
| 1 | Complete the 17-force economic engine | 17/17 research modules; max defensible executable forces; momentum for productivity; uncertainty contract; dependency map | **COMPLETE** — 9 level-published + 2 dimension-only + 6 context profiles + 0 deferred (17 total); dependency map + force matrix reproducible; uncertainty endpoint + history live |
| 2 | Big Cycle engine + Research Lab | Experimental composite engine; `/research` live; transition rules researched; experimental isolation | **COMPLETE** — registry + 4 composite models + phase/stage classifier + /research UI live, all experimental-gated; retrospective diagnostics manifest generated (4 models × 8 countries) |
| 3 | Complete Astro + Liquid Glass app | Workspace completion (drag/resize/lock), all widgets on real data, component showcase | **MOSTLY COMPLETE** — workspace filters inherited by widgets, pointer drag/resize/lock/undo/redo Playwright-verified, Add to Workspace on key pages, Data Explorer + compare with exports, uncertainty band charts; search/settings/showcase remain (Mission 4 P2) |
| 4 | Historical validation + forecasting | Release-date discipline, as-of queries, backtest-safety evidence, gated forecast architecture | **IN PROGRESS** — execution modes (current/retrospective/strict/assumption) threaded through alignment→normalizer→forces→composites; provider release-evidence matrix; leakage tests; validation API (execution-modes, release-evidence, availability, reference-availability, diagnostics); RL historical-validation section; forecasting scaffolding pending |
| 5 | Market regime research + strategy + paper trading | Market regimes, asset-class analysis, historical strategy research, isolated paper trading, final integration | **COMPLETE** — 35-instrument market layer with real FRED data (~63k obs from 2000); as-of FX conversion; growth×inflation regime engine + history/asset-returns APIs; monthly-grid simulator with next-period + FX-gated execution; Decimal paper ledger + watchlist; /forecast readiness gates (all gated today); 5 new Astro pages, browser-verified |
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
- [x] Forecast readiness report — /api/research/forecast/readiness + /forecast page; all horizons gated on evidence (no fabricated probabilities)
- [ ] Search, settings, component showcase (P2)
- [x] Browser screenshots + performance/accessibility audit — .dev/review/m5-*.png; a11y spec (single h1, labeled controls, named buttons, img alt) green on all 5 new pages; perf within existing envelope (~16MB dev vs 24MB on /cycle)
- [x] PR #1 update + consolidated acceptance report — .dev/MISSION5_ACCEPTANCE.md

## Mission 5 delivered to date (this session)

- **§8 resolved as reporting artifact**: 2015-window runs produced `stage=None` (min_observations=12 gate), which read as "stable"; with the 2000 window the classifiers produce 36–42 genuine transitions/model, 15–19 post-2015. Manifest now reports classification availability; regression test added.
- **§6–7 release evidence**: STRICT_AS_OF accepts `retrieved_at ≤ cutoff` ("atlas_retrieved"); ingestion-run content checksums; `scripts/collect_snapshot.py` prospective vintage collector; availability endpoint reports retrieved-evidence counts.
- **§9 sensitivity**: 108-config grid re-classified from diagnostics — 5–102 transitions, thresholds unvalidated; no config yields forecast-trainable samples.
- **Market data (§14–18)**: `app/market/` — 35 instruments (8 country equity indices, US/DE/GB/JP/CH yields + policy rates, corp + HY, 6 FX pairs, commodity index), FRED adapter, idempotent ingestion, ~63k observations from 2000; ISO3→ISO2 mapping fix (CHN was pulling CHE equity).
- **Asset research (§23–25)**: returns/vol/drawdown stats, rolling stats, shared-date correlation matrix, as-of FX conversion via USD legs — instrument `return_methodology` governs every response (a yield is never a return).
- **Regimes (§19–22)**: experimental growth×inflation engine (4 regimes + UNCLASSIFIED, sub-eps carry-forward), financial-conditions panel, per-country history + regime-bucketed equity returns; explicitly association-not-causation.
- **Strategy engine (§26–31)**: benchmark strategies + monthly-grid simulator — next-period execution (decision at T trades at first price after T), FX-gated joint execution, transaction costs, long-only/unleveraged, bounded ranges, §30 result contract with run manifest.
- **Paper portfolio (§32–36)**: isolated Decimal ledger (paper_* tables), idempotent transactions, stored-price or flagged manual prices only, valuation with average-cost basis, watchlist endpoints — simulation=True on every response.
- **Forecast surface (§10–13)**: typed contracts + per-model/horizon readiness evaluator (5 gates); /forecast page renders gate failures verbatim; forecast probe returns availability + evidence, `stage_probabilities: null` by design.
- **Frontend (§37–45)**: /forecast, /markets, /strategies, /portfolio, /watchlist pages + nav; typed API client with POST/DELETE; badge-ok/badge-err tokens; 5 new routes added to Playwright suite (39 pass).
- **Bugfix**: simulator FX-gated execution — entry slips to first jointly executable point instead of silently skipping; `_stats` zero-base guards; regression test.

## Remaining (Mission 5)

- [x] collect_snapshot.py live run complete — 4 live providers swept (world_bank/bis/oecd/imf_weo); hundreds of NEW + REVISED vintages captured incl. IMF WEO re-vintage (200 revised obs); WID skipped (bulk-file provider, --wid-zip opt-in). Live run also exposed + fixed an IMF SDMX-JSON schema drift (attributes.dimensionGroup).
- [ ] Regime/macro-signal strategies stay gated pending release-date evidence (§31)
- [ ] Performance + accessibility audit of new pages
- [x] Final regression totals + PR update + §55 report — .dev/MISSION5_ACCEPTANCE.md
