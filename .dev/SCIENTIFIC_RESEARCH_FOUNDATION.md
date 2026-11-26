# Scientific Research Foundation — Public Release Phase 1

Date: 2026-11-25
Branch: `feature/great-power-observatory`

This phase moves Atlas from descriptive monitoring toward auditable
hypothesis testing. It does **not** prove the Big Cycle theory and does
not make the Observatory's stage labels validated historical facts.

## Implemented architecture

| Layer | Implementation | Status |
|---|---|---|
| Theory registry | `theory_registry_entries`; seeded `theory-registry-v1.0` | 7 entries |
| Hypothesis protocols | `hypothesis_protocols`, unique on `hypothesis_code + protocol_version` | H01–H04 registered |
| Research observations | `research_observations` | 111,546 JST R6 rows |
| Independent outcomes | `crisis_events`, `crisis_coverage` | 88 systemic-banking-crisis onsets; 2,668 explicit covered country-years |
| Research population | `research_population_memberships` | 8 primary + 18 JST entities (26 rows) |
| Immutable ledger | `prediction_ledger_entries`, `prediction_outcomes` | 1,666 scored rows and outcomes |
| Evaluation results | `evaluation_results` | H01 executed; latest result honestly negative |
| Evidence status | `evidence_status_entries` | 6 public measurement classes |
| Dataset rights | `dataset_rights_registry` | JST, ALFRED/FRED, IMF WP-2026-094 reviewed |
| Research API | `/api/research-foundation/*` | Implemented |
| Export | `scripts/export_research.py` → `.dev/reports/export` | Regenerated |

Alembic migration: `f30725ab4c2d` (`add scientific research foundation`).

## Theory registry decisions

- Ray Dalio's source concepts are separated into the broad Big Cycle,
  money/credit/debt, internal-order and external-order claims.
- The 17 Atlas forces and eight Atlas stages are explicitly
  `atlas_operational_framework` entries, not quotations of Dalio's
  original stage structure.
- `cycle_duration_approximately_75_years` is a falsifiable candidate
  claim only. It is currently `untestable_with_current_evidence` and is
  never used to advance stages or compute a countdown.

## Imported data

### JST Macrohistory Database R6

- Official workbook verified and imported from
  `https://www.macrohistory.net/app/download/9834512569/JSTdatasetR6.xlsx`
- SHA-256: `c1bb91fe56ea50d4f27af5c0fc897d481e89ae38ce41eaecab62134c9354981d`
- 18 advanced-economy entities, 1870–2020, 2,718 source rows
- Imported **111,546 non-null research observations** across the workbook's
  numeric variables
- Imported **88 current-coding systemic banking crisis onsets**
  (`crisisJST = 1` only in the onset year)
- Imported **2,668 coverage rows** where a non-event means covered
  no-event, not unknown
- Release evidence is dataset-level only: R6 publication date, not a
  claim that each annual value was publicly available in its historical year.
- License: CC BY-NC-SA 4.0, attribution required, commercial use and
  direct raw redistribution restricted.

## Blocked or incomplete sources

| Source | Status | Precise blocker |
|---|---|---|
| ALFRED/FRED vintages | Adapter and CLI implemented | A registered 32-character FRED API key is required. `BCA_FRED_API_KEY` is not configured and no credential is committed. |
| IMF WP/2026/94 systemic banking crises | Local ZIP/CSV importer implemented | The advertised official ZIP `https://www.imf.org/-/media/files/publications/wp/2026/datasets/wp2694.zip` returned HTTP 404 during verification. No local official bundle was supplied. |
| Other crisis types | Registry supports banking/currency/sovereign/recession/other | No verified dataset was imported in this phase; JST banking onsets remain separate. |
| Strict historical replay | Contract and eligibility model retained | Strict provider release evidence remains unavailable for the existing macro panel; first Atlas retrieval is evidence of Atlas possession, not original publication. |

These are reported blockers, not gaps filled with fabricated data.

## H01 protocol and result

Protocol `H01-P1.0` is a retrospective research protocol, not a historical
pre-registration. Predictor: five-year change in JST `debtgdp` at the
forecast origin. Outcome: source-defined JST systemic-banking-crisis onset
within 1, 2 or 5 years. Split: chronological train through 1989, test
1990–2020.

Latest registered evaluation:

- Result state: `no_evidence_of_improved_predictive_value`
- Test events per horizon: 19
- Test base rate: ~3.4%
- AUC: 1y `0.363`, 2y `0.381`, 5y `0.296`
- Top-quintile precision: `1.54%`, `1.50%`, `0.88%`

The univariate debt-growth benchmark performed below random ordering and
below the unconditional base rate in the held-out period. This is a valid
scientific result and is preserved in the immutable evaluation registry.
An earlier exploratory-state evaluation row is also preserved because the
ledger is append-only; the `*:v2` evaluation is the current interpretation.

## Leakage and population controls

- Predictor period must be before the outcome year.
- Dataset version is fixed (`jst_macrohistory/R6`).
- Forecast origins are explicit and ledger rows are content-checksummed.
- Crisis onset is separate from ongoing crisis state.
- Explicit `CrisisCoverage` prevents undocumented country-years from being
  treated as crisis-free.
- JST population membership is source-defined; countries were not selected
  after inspecting their crisis outcomes.
- Correlated international crises are documented as non-independent
  observations, not counted as independent experiments.

## Three research timescales

Registered candidate clocks:

1. `short_economic_financial` — 1–5 years
2. `medium_institutional_financial` — 5–25 years
3. `long_historical_big_cycle` — 25–500 years

All are `candidate_definition_not_natural_law`. The existing four
national-condition models remain experimental and are not relabelled as
validated Big Cycle stages.

## Commands

```powershell
# Historical/research import path
Update.bat -Historical
Update.bat -Historical -JstFile .dev\tmp\JSTdatasetR6.xlsx
Update.bat -Historical -ImfCrisisFile path\to\official-wp2694.zip

# Direct scripts from apps/api
.venv\Scripts\python.exe scripts\import_jst_macrohistory.py
.venv\Scripts\python.exe scripts\ingest_alfred.py --vintages 5 GDP CPIAUCSL UNRATE USREC
.venv\Scripts\python.exe scripts\import_imf_banking_crises.py --file path\to\wp2694.zip
.venv\Scripts\python.exe scripts\run_h01_evaluation.py
.venv\Scripts\python.exe scripts\export_research.py
```

`Update.bat -Historical` downloads the public JST R6 workbook when no
local file is provided, skips ALFRED unless `BCA_FRED_API_KEY` is set,
skips IMF unless `-ImfCrisisFile` is supplied, registers H01 idempotently,
and keeps provider failures independent.

## Export package

The regenerated export contains the theory registry, hypothesis protocols,
research population, historical vintage inventory, crisis chronology and
coverage, prediction ledger/outcomes, evaluation results, evidence status,
dataset rights, research timescales and the standard Atlas manifests.

Generated under `.dev/reports/export/` and summarized by
`.dev/reports/research_manifest.json`.

## Verification — 2026-11-26

- Backend pytest: **837 passed**
- Vitest: **54 passed**
- Astro check: **0 errors / 0 warnings / 0 hints**
- Production build: **38 pages built**
- Playwright against native production server: **57 passed**
- Native API production check: `/health` connected and validation endpoints returned 50 questions plus the Q11 detail with related H01 protocols/evaluations
- Previous verification retained: 834 backend checks, 55 Playwright checks and provider/update dry runs on 2026-11-25

## Validation question registry — 2026-11-26

A canonical immutable question registry now extends this foundation without
creating a second research engine.

- Registry version: `validation-questions-v1.0`
- Questions: **50**
- Categories: core theory `10`, debt and money `15`, internal conflict `10`, external rivalry `10`, technology and shocks `5`
- Implementation recount: `data_available` 13, `evaluation_implemented` 2, `not_implemented` 4, `partially_implemented` 26, `research_method_implemented` 5
- Scientific-status recount: `currently_untestable` 26, `evidence_inconsistent_with_registered_claim` 3, `exploratory_findings` 1, `insufficient_evidence` 5, `untested` 15
- Database table: `validation_questions` (Alembic `b48ac2e91f01`), versioned by `(question_code, registry_version)` and content-checksummed
- API: `/api/research/foundation/validation/questions`, `/validation/questions/{code}`, `/validation/summary`
- Interface: `/research/validation`; homepage research-evidence summary; workspace widgets `validation-coverage` and `validation-questions`
- Exports: `validation_questions.json`, `question_evidence_matrix.{json,csv}`, `dataset_dependency_matrix.csv`, `missing_data_inventory.{json,csv}`, `validation_summary.json`
- Canonical registry copy: `.dev/VALIDATION_QUESTION_REGISTRY.json`
- Per-question assessment: `.dev/THEORY_VALIDATION_50.md`

Because the original supplied question wording was absent from the repository,
the registry explicitly records `wording_origin: atlas_derived_v1`. It is a
canonical Atlas wording v1, not a recovered legacy source text. The prior
assessment only preserved aggregate counts (5 implemented, 23 partially
addressed, 22 missing), so the current recount uses actual registry/database
statuses rather than inventing per-question previous statuses.

The UI states implementation coverage and scientific status separately. A
registered dataset, chart or endpoint does not mark a question as scientifically
answered; missing datasets and contradictory evidence remain visible.
