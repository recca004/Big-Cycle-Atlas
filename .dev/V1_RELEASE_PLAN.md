# Big Cycle Atlas — Road to v1.0

Current programme state: **all six missions delivered — v1.0.0-rc.1 ready for owner review** (2026-11-25). Acceptance reports: .dev/MISSION5_ACCEPTANCE.md, .dev/MISSION6_RELEASE.md. PR #1 `feature/big-cycle-atlas-astro-v2` open/mergeable.

## The six missions

| # | Mission | Gate | Status |
|---|---------|------|--------|
| 1 | Complete the 17-force economic engine | 17/17 research modules; max defensible executable forces; momentum for productivity; uncertainty contract; dependency map | **COMPLETE** — 9 level-published + 2 dimension-only + 6 context profiles + 0 deferred (17 total); dependency map + force matrix reproducible; uncertainty endpoint + history live |
| 2 | Big Cycle engine + Research Lab | Experimental composite engine; `/research` live; transition rules researched; experimental isolation | **COMPLETE** — registry + 4 composite models + phase/stage classifier + /research UI live, all experimental-gated; retrospective diagnostics manifest generated (4 models × 8 countries) |
| 3 | Complete Astro + Liquid Glass app | Workspace completion (drag/resize/lock), all widgets on real data, component showcase | **COMPLETE** — everything in the Mission 3 row plus: global search (Ctrl+K palette + /api/search), versioned local preferences + Settings page, dev-only component showcase, historical-validation workspace widget (Mission 6) |
| 4 | Historical validation + forecasting | Release-date discipline, as-of queries, backtest-safety evidence, gated forecast architecture | **COMPLETE (with evidence gates)** — all API surfaces live + historical-validation widget; forecast surface returns gated-unavailable by design (no fabricated probabilities — an evidence limitation, not missing software) |
| 5 | Market regime research + strategy + paper trading | Market regimes, asset-class analysis, historical strategy research, isolated paper trading, final integration | **COMPLETE** — 35-instrument market layer with real FRED data (~63k obs from 2000); as-of FX conversion; growth×inflation regime engine + history/asset-returns APIs; monthly-grid simulator with next-period + FX-gated execution; Decimal paper ledger + watchlist; /forecast readiness gates (all gated today); 5 new Astro pages, browser-verified |
| 6 | QA, self-hosting, v1.0 release prep | Full regression, deployment docs, release checklist | **COMPLETE** — native-first deployment (Windows launchers + Linux systemd docs), prod verified end-to-end incl. owner acceptance browser walkthrough (21/21), backup/restore drill, 798+43+44 tests green, docs+CI+PR updated. Docker demoted to optional-unverified |

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

- [x] Historical-validation widget(s) in workspace registry — shipped Mission 6 (HistoricalValidationWidget, registry doc regenerated)
- [x] Forecast readiness report — /api/research/forecast/readiness + /forecast page; all horizons gated on evidence (no fabricated probabilities)
- [x] Search, settings, component showcase (P2) — shipped Mission 6
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
- [ ] Regime/macro-signal strategies stay gated pending release-date evidence (§31) — **evidence gate, not a software task**: stays closed until provider release dates are ingested
- [x] Performance + accessibility audit — a11y spec green on all new pages; EChart chunk tree-shaken 1096→532KB (+gzip 180KB on the wire)
- [x] Final regression totals + PR update + §55 report — .dev/MISSION5_ACCEPTANCE.md


## Mission 6 delivered (this session)

- Native-first deployment: serve.py single-process prod (API+built frontend, gzip), Windows launchers (Setup/Start/Start-Prod/Stop/Update/Upgrade/Backup/Restore/Test/Status), Task Scheduler installer (approval-gated), Linux systemd units + DEPLOYMENT.md (unverified on Linux)
- Global search endpoint + Ctrl+K palette; versioned prefs (theme/motion/transparency/defaults) + Settings rewrite; historical-validation widget; dev-only showcase
- Correctness: portfolio row-lock concurrency fix; alembic migration gap closed (market/paper/watchlist); /api/indicators + /api/search bare+slashed route fix (prod 404s found in owner walkthrough)
- Ops: backup→isolated-restore drill (14 tables identical, API against restored DB); retention policy (BCA_BACKUP_KEEP, pinned bca-keep-*.dump); GZip; TrustedHost (DNS-rebinding guard)
- Docs: README/DEPLOYMENT/OWNER_GUIDE/SECURITY/TROUBLESHOOTING/DATA_COLLECTION/RELEASE_NOTES; CI workflow; legacy Next.js removed
- Regression: 798 backend + 43 vitest + 44 playwright (incl. a11y) + astro check 0 — all green

## Genuinely unfinished (post-v1.0 backlog)

- Linux/Proxmox deployment not run on a live host; Docker path unverified (optional)
- Regime/macro strategies gated on release-date evidence (§31 — evidence, not code)
- ~455 pre-existing ruff findings in legacy diagnostic scripts
- WID.world bulk-ingest remains manual opt-in
