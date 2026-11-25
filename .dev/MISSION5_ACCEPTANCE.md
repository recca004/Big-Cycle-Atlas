# Mission 5 — Acceptance Report (§55)

Date: 2026-11-25 · Branch: `feature/big-cycle-atlas-astro-v2` · PR: #1
Remote HEAD: `0c26edc`

## Verdict

Mission 5 is **delivered**. The market-data layer, market-regime research,
asset-research APIs, strategy simulator, isolated paper-trading ledger and
forecast-readiness surface are live against real data, with honest gating
everywhere the evidence does not support a stronger claim. Forecasting
remains gated by design; regime/macro-signal strategies stay gated pending
release-date evidence (§31).

## What shipped

### §6–9 — Historical information availability (workstream A/B)

- STRICT_AS_OF accepts `retrieved_at ≤ cutoff` ("atlas_retrieved" evidence)
  in addition to provider `release_date`; both reported by the availability
  endpoint.
- `IngestionRun` carries `content_sha256`; revised values become new
  vintages (`vintage_number`, `supersedes_observation_id`,
  `IndicatorRevision`) — never overwrites.
- `scripts/collect_snapshot.py` — prospective vintage collector, ran live
  across all live providers. Captured hundreds of NEW/REVISED vintages,
  including a full IMF WEO re-vintage (200 revised observations across 8
  countries). WID is bulk-file and opts in via `--wid-zip`.
- §8 resolved as a reporting artifact, not a classifier defect:
  2015-window runs fail the `min_observations=12` gate (`stage=None` read
  as "stable"). The manifest now reports classification availability; the
  genuine counts are 36–42 transitions/model, 15–19 post-2015.
- §9 sensitivity grid (108 configs): 5–102 transitions — thresholds
  unvalidated; no config yields forecast-trainable samples.

### §10–13 — Forecast architecture

- Typed contracts + readiness evaluator with 5 gates (sample size,
  eligible origins, independent transitions, positive labels, strict
  availability) per model × horizon.
- `GET /api/research/forecast/readiness`, `/forecast/{iso3}`; `/forecast`
  page renders gate failures verbatim. All horizons gated today;
  `stage_probabilities: null` by design.

### §14–18 — Market data

- `app/market/`: 35 instruments (8 country equity indices, US/DE/GB/JP/CH
  yields + policy rates, corporate + HY, 6 FX pairs, commodity index),
  FRED adapter, idempotent ingestion, ~63,000 observations from 2000.
- As-of FX conversion via USD legs — never uses a rate from the future.

### §19–25 — Regimes + asset research

- Experimental growth×inflation regime engine (REFLATION / GOLDILOCKS /
  STAGFLATION / DISINFLATION_SLOWDOWN / UNCLASSIFIED, sub-eps
  carry-forward); financial-conditions panel; regime history and
  regime-bucketed equity returns — association, not causation.
- Returns/vol/drawdown, rolling stats, shared-date correlation —
  `return_methodology` governs every response (a yield is never a return).

### §26–31 — Strategy engine

- Benchmark strategies + monthly-grid simulator: next-period execution,
  FX-gated joint execution, transaction costs, long-only/unleveraged,
  bounded ranges, §30 result contract with full run manifest.

### §32–36 — Paper portfolio

- Isolated Decimal ledger (`paper_*` tables), idempotent transactions,
  stored-price or flagged manual prices only, average-cost valuation,
  watchlist. `simulation=True` on every response.

### §37–45 — Frontend

- `/forecast` `/markets` `/strategies` `/portfolio` `/watchlist` + nav;
  typed API client with POST/DELETE; review screenshots in `.dev/review/`.

## Defects found and fixed during delivery

- **CHN equity pulled CHE's series** — `iso3[:2]` collided CHN→"CH" with
  CHE. Fixed; wrongly-imported observations replaced.
- **Simulator FX-gated execution** — CHF-base simulations silently skipped
  the entry when the FX series started after the equity series (execution
  slipped past the schedule date). Now executes at the first *jointly
  priceable* point; `_stats` guards zero-base paths. Regression test added.
- **IMF SDMX-JSON schema drift** — attribute definition list moved from
  `attributes.dataAttributes` to `attributes.dimensionGroup`; the live
  snapshot run exposed it. Parser accepts either key (still strict).

## Regression totals

| Suite | Result |
|---|---|
| Backend pytest | **798 passed** (103s) |
| Vitest (web-astro) | **43 passed** |
| `astro check` | 0 errors |
| `astro build` | 36 pages |
| Playwright e2e | **39 passed** (incl. 5 new routes) |
| A11y audit spec | **5 passed** (single h1, labeled controls, named buttons, img alt — all new pages) |
| Perf (dev server) | new pages 43–52 reqs / ~16 MB — within existing envelope (/cycle: 72 reqs / 24 MB) |

## Live verification

- API smoke: instruments, returns, correlation, FX convert, regimes,
  regime-returns, forecast readiness, simulate (USD + CHF), portfolio
  txn round-trip, watchlist — all against real dev data.
- Browser: all 5 new pages render live data; interactive sim verified
  in USD and CHF (FX-adjusted result +59.3% vs naive USD view).
- Screenshots: `.dev/review/m5-*.png`.

## Honest limitations (unchanged by this mission)

- Zero provider release dates in the corpus → strict mode still reports
  most history unavailable; `retrieved_at` evidence accrues prospectively
  from the first snapshot run onward.
- Regime classifier thresholds (§9) are unvalidated — no config yields
  forecast-trainable samples today.
- Market coverage is FRED-only, monthly equity indices from 2000; no
  survivorship-corrected per-security data — returns are index-level.
- Paper trading is a ledger simulation, not a broker integration.
