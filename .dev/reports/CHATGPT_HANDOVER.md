# Big Cycle Atlas — compact ChatGPT handover

Generated: 2026-11-25T22:27:21.020278Z
Base commit: `71d3e0589d10f4c412549fcd56b8701d45a69b60`

This package contains the actual database inventory, latest-vintage raw histories, approved force evidence, four-model experimental cycle results, international-power measurements and forecast-gate evidence.

- Main report: `ATLAS_RESEARCH_1980_PRESENT.md`
- Country reports: `countries/USA.md`, `CHN.md`, `IND.md`, `JPN.md`, `DEU.md`, `GBR.md`, `FRA.md`, `CHE.md`
- Machine-readable package: `export/`
- Reproducibility manifest: `export/research_manifest.json`

## Key facts

- Raw GDP/population history reaches 1960; several trade/credit series reach 1970 or earlier.
- Valid experimental classifications begin around 1995–1996, not 1980.
- 24 inventory fields and 361 country-indicator coverage records were exported.
- 136 country-force rows and 1472 model-history points were exported.
- `model_b_domain` and `model_c_overlap` are materially equivalent under current data: 368 comparisons, 100.0% near-score and 100.0% stage agreement; they are not independent evidence.
- Indebtedness is a configured own-history measurement but 32 semantic exclusions prevent it entering the 0–100 cross-country composites.
- Strict release-date-safe scored periods: **0**; 21178 stored observation vintages are provenance, not forecast origins.
- Forecast output remains unavailable where readiness gates fail.

## Independent-review questions

Use the CSV/JSON exports to test: country rankings by dimension, long-run convergence/divergence, model agreement, USA–China transitions, India’s measurable expansion, missing-force evidence, and whether any leadership-transition forecast is defensible without release-date-safe samples.
