# Data Model

Milestone 1 implements only `countries`. The tables below define the full planned
schema so later milestones can build against it without rework.

## Implemented (Milestone 1)

### `countries`

| Column | Type | Notes |
|---|---|---|
| id | int PK | |
| iso3 | varchar(3) | unique, indexed |
| iso2 | varchar(2) | unique |
| name | varchar(120) | |
| region | varchar(60) | e.g. Europe, Asia, Americas |
| created_at | timestamptz | server default now() |
| updated_at | timestamptz | updated on change |

Seeded from `packages/shared/data/initial-countries.json` with the 8 initial
countries (USA, CHN, CHE, DEU, FRA, GBR, JPN, IND).

## Planned

### `data_sources`
Source registry: name, API base, auth requirements, update frequency, rate limit, status (planned/testing/active/broken). Mirrors `.dev/DATA_SOURCES.md`.

### `indicators`
Canonical indicator catalog: code (e.g. `GDP_GROWTH`), name, unit, category, direction meaning, source metadata.

### `observations`
Raw observations exactly as retrieved — never overwritten:

```
country | indicator | period | value | unit | source |
observation_date | release_date | retrieved_at
```

`release_date` enables point-in-time backtests ("what did the model know at date X?").

### `indicator_revisions`
Revisions to previously released values, keyed by (indicator, country, period, revision date). Backtesting must use the revision that was public at the test date.

### `forces`
The 17 forces: key, name, description, positive/negative state descriptions.

The 17 forces:
1. Leadership capabilities
2. Education
3. Character / determination
4. Rule of law
5. Corruption
6. Resource allocation efficiency
7. Global openness
8. Productivity / output growth
9. Cost competitiveness
10. Trade and capital flows
11. Infrastructure and investment
12. Indebtedness
13. Military strength
14. Wealth / opportunity / values gaps
15. Internal conflict
16. Geography
17. Acts of nature

All force scores use the same orientation: **100 = strong/healthy, 0 = weak/stressed**.
Raw indicators where a high value means weakness (e.g. government debt/GDP,
corruption index, internal conflict) are inverted during normalization.

### `force_indicator_mappings`
Config-driven mapping (not hardcoded logic): force → indicator, weight, direction, transform, freshness rules.

Example:

```
education:
  - tertiary_attainment
  - average_years_schooling
  - test_scores
  - stem_share

indebtedness:
  - government_debt_gdp
  - household_debt_gdp
  - corporate_debt_gdp
  - debt_service_ratio
  - credit_gap
```

### `force_scores`
Per force, per country, per period: score (0–100), trend (strongly rising / rising / stable / falling / strongly falling), momentum, confidence, data coverage, last updated.

### `cycle_scores`
Master cycle values per country/period:

- `power_score`
- `cycle_momentum`
- `debt_stress`
- `internal_stress`
- `relative_power_score`
- `phase` (public: RISE / PEAK / DECLINE)
- `stage` (internal: EARLY_RISE, RISE, LATE_RISE, PEAK, LATE_PEAK, EARLY_DECLINE, DECLINE, RESET)
- `phase_confidence`

Phase derivation uses power level + trend + momentum + debt stress + internal
stress + relative strength + confidence — never a single raw score.

### `cycle_forecasts`
Probability windows for leaving the current stage within 1/2/5/10 years, plus
most-likely-next-stage. Interface only until a tested model exists (Milestone 8).

### `model_versions`
Versioned scoring configurations (e.g. `cycle-model-v0.1`). Every stored result
references the model version that produced it.

### `ingestion_runs`
Per-source run log: started_at, completed_at, success, rows_received,
rows_inserted, rows_updated, errors (JSON). Powers a future admin data-health page.

### `calculation_runs`
Per-run record of scoring calculations: model version, inputs snapshot, timing,
status.

## Absolute vs relative scores

A country can improve while losing ground to others. Force/cycle scoring stores
both `absolute_score` and `relative_score` (vs. the tracked country set). The UI
must clearly separate **domestic strength** from **relative position**.