# Force Aggregation Methodology

Sprint 5.21 — 2026-09-10. Methodology + typed configuration only. No force
calculation, no force persistence, no force API. Companion to
`.dev/NORMALIZATION.md` (indicator-level) and `.dev/FORCE_COVERAGE.md`
(data coverage). This document answers ONE question:

> **When is Atlas allowed to publish a numeric force signal?**

The answer is NOT "whenever one or more mapped indicators have numbers."
Different normalized indicators have different economic semantics, and a
raw observation can never enter force aggregation directly.

**Sprint 5.22 implementation note (2026-09-10):** Sprint 5.22 implemented
the first executable ForceSignal layer using ONLY this methodology. 3 of 17
forces are now executable (Rule of law, Corruption, Internal conflict proxy
via IDENTITY_SINGLE); 14 of 17 are intentionally None. The ForceSignal type
lives in `app/cycle/force_signal.py`; the pure aggregator is
`aggregate_force_from_signals`; the service orchestrator is
`build_force_signals_as_of` in `app/services/force_signal_service.py`. No
force persistence, no public force API. force-aggregation-v0.1 unchanged
(implementation faithfully executes the already-approved methodology).

**Sprint 6.1 audit note (2026-09-10, DEC-030):** Sprint 6.1 audited whether
Indebtedness can defensibly receive a composed `level_score` from DSR
(CORE_CONDITION) + credit-gap (VULNERABILITY_PENALTY) + government-debt
(SUPPORTING_CONTEXT). Verdict: **DEFER_INDEBTEDNESS_COMPOSITION**.
Government-debt normalization is a hard prerequisite (the stock measure is
the dominant differentiator when DSR is similar; JPN 214% vs CHE 39% have
comparable DSR stress). Every candidate composition structure either
requires arbitrary parameters, mishandles the credit-gap neutral-50
semantics, or improperly ignores government debt. Indebtedness stays
DEFERRED_MULTI with level=None. force-aggregation-v0.1 unchanged. Next:
Sprint 6.2 government-debt normalization methodology audit.

## 1. Permanent force-layer invariants

These rules are permanent. They cannot be relaxed by a future sprint
without an explicit methodology decision (a new DEC) that overrides them.

### 1.1 Dimensions remain separate

Force output must preserve four independent dimensions:

- `level_score`
- `relative_score`
- `momentum`
- `confidence`

Never collapse them into a single "force score." Prohibited:

- `overall = level + relative + momentum`
- `score *= confidence`
- `momentum *= confidence`
- `level *= coverage`

A future sprint may design an explicit composite ONLY if it documents the
formula, the weights, and the justification, and only after the
component dimensions are individually validated. Sprint 5.21 approves no
composite.

### 1.2 Coverage != strength

Coverage status remains:

- `AVAILABLE`
- `PARTIAL`
- `DEFINED_NOT_SOURCED`
- `MISSING`

Coverage does NOT numerically alter `level_score`. A force may have:

```
level_score = 82
coverage    = PARTIAL
```

That means: the measured/proxy component is strong, but conceptual force
measurement is incomplete. It must NOT become `82 * some_partial_factor`.
Proxy ceilings (DEC-009) remain completeness semantics, not numeric
penalties.

### 1.3 Missing != zero

Missing or unapproved force dimensions are `None`, never `0`. Never assign
an arbitrary neutral 50 to missing force inputs. The credit-gap indicator's
approved 50 (DEC-021) has a specific INDICATOR-LEVEL meaning (no-excess
region is neutral, not a health claim) and must NOT be generalized into a
missing-data rule at the force layer.

### 1.4 Only executable normalized signals may enter numeric aggregation

Required layering:

```
Observation → AlignedValue → NormalizedSignal → ForceSignal
```

Never `Observation → ForceSignal`. A raw observation cannot enter force
aggregation directly. A mapped live indicator whose normalization is
`CONTEXTUAL_DEFERRED` or otherwise unimplemented may appear as supporting
provenance/context, but contributes NO numeric value.

## 2. Indicator role taxonomy

A typed role enum classifies how each mapped indicator may participate in
force aggregation.

| Role | Semantics |
|---|---|
| `CORE_CONDITION` | A normalized 0-100 condition whose direction is higher = stronger. Eligible for force level aggregation under an explicitly approved aggregation rule. |
| `PROXY_CONDITION` | Same numeric orientation as CORE_CONDITION, but measures only a narrower proxy for the conceptual force. Requires the force's coverage/proxy semantics to expose that incompleteness (PARTIAL ceiling). |
| `VULNERABILITY_PENALTY` | A signal representing an asymmetric vulnerability/risk component. Must NOT be naively averaged with CORE_CONDITION. Requires a force-specific composition formula before it may affect force level. |
| `SUPPORTING_CONTEXT` | Relevant raw/normalized context without approved numeric contribution to the force aggregate. |

No additional roles are invented in Sprint 5.21. If future live semantics
require a new role, it is an explicit methodology decision.

## 3. Initial role assignments

Audit of all current force mappings. Every mapped live indicator is
classified honestly.

### Rule of law

| Indicator | Role | Reason |
|---|---|---|
| `RULE_OF_LAW_WGI_SCORE` | `CORE_CONDITION` | DIRECT_0_100 level + relative + momentum executable (normalization-v0.6). Higher = stronger. Force semantics genuinely inherit the indicator semantics. |

### Corruption

| Indicator | Role | Reason |
|---|---|---|
| `CONTROL_OF_CORRUPTION_WGI_SCORE` | `CORE_CONDITION` | DIRECT_0_100 level + relative + momentum executable. Higher = stronger. Force semantics genuinely inherit the indicator semantics. |

### Internal conflict

| Indicator | Role | Reason |
|---|---|---|
| `POLITICAL_STABILITY_WGI_SCORE` | `PROXY_CONDITION` | Measures political stability / absence of violence — a useful institutional/conflict-risk proxy, but does NOT fully represent internal conflict (polarization, protests, distributional tension). Coverage stays PARTIAL (DEC-009). DIRECT_0_100 level + relative + momentum executable. |

### Indebtedness

| Indicator | Role | Reason |
|---|---|---|
| `DEBT_SERVICE_RATIO` | `CORE_CONDITION` | OWN_HISTORY level executable (normalization-v0.5). Higher DSR = greater burden = weaker. Full own-history condition score. No relative, no momentum. |
| `CREDIT_TO_GDP_GAP` | `VULNERABILITY_PENALTY` | ONE_SIDED_VULNERABILITY level executable (normalization-v0.6). Asymmetric vulnerability signal with neutral 50. Must NOT be naively averaged with DSR. |
| `GOVERNMENT_DEBT_GDP` | `SUPPORTING_CONTEXT` | Numeric normalization deferred (CONTEXTUAL_DEFERRED). Raw level input only — no monotonic "higher debt = weaker" curve is approved. |

### All other mapped indicators

Every other mapped live indicator has level normalization `CONTEXTUAL_DEFERRED`
(or no executable level at all). They are classified `SUPPORTING_CONTEXT`
unless a different non-numeric role is methodologically justified.

| Force | Indicators | Role | Reason |
|---|---|---|---|
| Education | `TERTIARY_ATTAINMENT_25_34` | `SUPPORTING_CONTEXT` | No level normalization approved. |
| Productivity / output growth | `GDP_GROWTH`, `LABOUR_PRODUCTIVITY_PER_HOUR` | `SUPPORTING_CONTEXT` | Level CONTEXTUAL_DEFERRED. |
| Cost competitiveness | `UNIT_LABOUR_COST_GROWTH`, `INFLATION_CPI` | `SUPPORTING_CONTEXT` | Level CONTEXTUAL_DEFERRED. |
| Trade and capital flows | `EXPORTS_GDP`, `IMPORTS_GDP`, `TRADE_BALANCE`, `CURRENT_ACCOUNT_GDP` | `SUPPORTING_CONTEXT` | Level CONTEXTUAL_DEFERRED. |
| Infrastructure and investment | `GROSS_CAPITAL_FORMATION_GDP` | `SUPPORTING_CONTEXT` | Level CONTEXTUAL_DEFERRED. |
| Military strength | `MILITARY_EXPENDITURE_USD`, `MILITARY_EXPENDITURE_GDP` | `SUPPORTING_CONTEXT` | Level CONTEXTUAL_DEFERRED; force capped PARTIAL. |
| Wealth / opportunity / values gaps | `GINI_INDEX`, `WEALTH_SHARE_TOP_10` | `SUPPORTING_CONTEXT` | Level CONTEXTUAL_DEFERRED; force capped PARTIAL. |

No existing indicator normalization methodology is changed.

## 4. Aggregation modes

A typed aggregation mode controls when a force may publish a numeric signal.

### 4.1 IDENTITY_SINGLE

The ONLY force-level numeric aggregation approved in Sprint 5.21.

Allowed when:
- force config explicitly approves it
- exactly ONE numeric component is the approved scoring component
- component role is `CORE_CONDITION` or `PROXY_CONDITION`
- component's `NormalizedSignal.level_score` is not `None`
- no second numeric component requires composition
- force score semantics genuinely inherit the indicator semantics

Formula:

```
force.level_score = indicator.level_score
```

No rescaling. No weighting. No averaging. This is not a mathematical
"model"; it is a transparent identity mapping.

### 4.2 DEFERRED_MULTI

Used whenever:
- 2+ numeric components require composition
- a vulnerability penalty must interact with a condition score
- relative dimensions would require cross-indicator combination
- momentum dimensions would require cross-scale combination
- weights are unresolved

Result: `force dimension = None` while component signals remain visible
in provenance. Do not pick equal weights merely because no weights exist.

## 5. Initial force-level approval matrix (17 forces)

| # | Force | Coverage ceiling | Mapped indicators | Roles | Exec level | Exec relative | Exec momentum | Aggregation mode | Level approved? | Relative approved? | Momentum approved? | Why |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Leadership capabilities | — | — | — | — | — | — | (unconfigured) | NO | NO | NO | No live indicators |
| 2 | Education | PARTIAL | `TERTIARY_ATTAINMENT_25_34` | SUPPORTING_CONTEXT | — | — | — | DEFERRED_MULTI | NO | NO | NO | Level normalization deferred |
| 3 | Character / determination | — | — | — | — | — | — | (unconfigured) | NO | NO | NO | No live indicators |
| 4 | Rule of law | — | `RULE_OF_LAW_WGI_SCORE` | CORE_CONDITION | YES | YES | YES | IDENTITY_SINGLE | YES | YES | YES | Single WGI core condition; identity inherits semantics |
| 5 | Corruption | — | `CONTROL_OF_CORRUPTION_WGI_SCORE` | CORE_CONDITION | YES | YES | YES | IDENTITY_SINGLE | YES | YES | YES | Single WGI core condition; identity inherits semantics |
| 6 | Resource allocation efficiency | — | — | — | — | — | — | (unconfigured) | NO | NO | NO | No live indicators |
| 7 | Global openness | — | — | — | — | — | — | (unconfigured) | NO | NO | NO | No live indicators (trade data is candidate context only) |
| 8 | Productivity / output growth | — | `GDP_GROWTH`, `LABOUR_PRODUCTIVITY_PER_HOUR` | SUPPORTING_CONTEXT ×2 | — | — | — | DEFERRED_MULTI | NO | NO | NO | Level normalization deferred; 2 components |
| 9 | Cost competitiveness | — | `UNIT_LABOUR_COST_GROWTH`, `INFLATION_CPI` | SUPPORTING_CONTEXT ×2 | — | — | — | DEFERRED_MULTI | NO | NO | NO | Level normalization deferred; 2 components |
| 10 | Trade and capital flows | — | `EXPORTS_GDP`, `IMPORTS_GDP`, `TRADE_BALANCE`, `CURRENT_ACCOUNT_GDP` | SUPPORTING_CONTEXT ×4 | — | — | — | DEFERRED_MULTI | NO | NO | NO | Level normalization deferred; 4 components |
| 11 | Infrastructure and investment | — | `GROSS_CAPITAL_FORMATION_GDP` | SUPPORTING_CONTEXT | — | — | — | DEFERRED_MULTI | NO | NO | NO | Level normalization deferred |
| 12 | Indebtedness | — | `DEBT_SERVICE_RATIO`, `CREDIT_TO_GDP_GAP`, `GOVERNMENT_DEBT_GDP` | CORE_CONDITION + VULNERABILITY_PENALTY + SUPPORTING_CONTEXT | DSR only | — | — | DEFERRED_MULTI | NO | NO | NO | DSR + credit gap cannot be naively averaged; government debt unscored; no composition formula approved |
| 13 | Military strength | PARTIAL | `MILITARY_EXPENDITURE_USD`, `MILITARY_EXPENDITURE_GDP` | SUPPORTING_CONTEXT ×2 | — | — | — | DEFERRED_MULTI | NO | NO | NO | Level normalization deferred; force capped PARTIAL |
| 14 | Wealth / opportunity / values gaps | PARTIAL | `GINI_INDEX`, `WEALTH_SHARE_TOP_10` | SUPPORTING_CONTEXT ×2 | — | — | — | DEFERRED_MULTI | NO | NO | NO | Level normalization deferred; force capped PARTIAL |
| 15 | Internal conflict | PARTIAL | `POLITICAL_STABILITY_WGI_SCORE` | PROXY_CONDITION | YES | YES | YES | IDENTITY_SINGLE | YES | YES | YES | Single WGI proxy condition; identity inherits semantics; coverage stays PARTIAL |
| 16 | Geography | — | — | — | — | — | — | (unconfigured) | NO | NO | NO | No live indicators |
| 17 | Acts of nature | — | — | — | — | — | — | (unconfigured) | NO | NO | NO | No live indicators |

**Summary: 3 forces approved for IDENTITY_SINGLE level + relative + momentum
(Rule of law, Corruption, Internal conflict proxy). 14 forces deferred.**

## 6. Relative score policy

Relative score remains separate from level. Sprint 5.21 may approve
relative force output ONLY under identity mapping:

- one approved component
- component `relative_score` exists
- force config explicitly permits identity copy

Copy the entire provenance:
- `reference_universe_id`
- `reference_universe_expected_n`
- `reference_universe_usable_n`
- `relative_rank` if present

Never recompute ranks at the force layer. Never average relative scores
across indicators. Never label `tracked_8` as global.

Approved for: Rule of law, Corruption, Internal conflict proxy only.

## 7. Momentum policy

Momentum may be copied through IDENTITY_SINGLE only. Do NOT aggregate
momentum from multiple indicators. DEC-016 explicitly says WGI momentum is
WGI-scale-specific and not approved for direct cross-indicator aggregation.

Approved for: Rule of law, Corruption, Internal conflict proxy (inherit
the same WGI 5y momentum under identity mapping).

Indebtedness: `momentum = None`. No DSR momentum. No credit-gap momentum.
No combination.

## 8. Confidence policy

Force confidence remains `None`. DEC-023 deferred numeric WGI indicator
confidence. No force-confidence numeric composition exists.

Do NOT use:
- `freshness_factor` as force confidence
- coverage percentage as force confidence
- proxy ceiling as a numeric confidence penalty
- source quality constants
- number of available indicators / expected indicators

Keep qualitative/provenance information separate.

## 9. Backtest safety

Force signal must carry `backtest_safe`. Initial policy: `False`
everywhere, because underlying indicator signals remain CURRENT/RESEARCH
rather than release-date-safe historical signals.

If later implemented generically: force `backtest_safe` may only be `True`
if every contributing component is backtest-safe AND force methodology
itself is historically version-safe. For current data this remains `False`
everywhere.

## 10. Versioning

Two separate version layers:

- Indicator normalization version: `normalization-v0.6` (unchanged)
- Force aggregation version: `force-aggregation-v0.1`

A future `ForceSignal` records BOTH. Sprint 5.21 itself changes no
executable economic output — `force-aggregation-v0.1` is the methodology
+ typed configuration version, not a scored-output version.

## 11. ForceSignal type design (not executed)

Designed but NOT executed in Sprint 5.21:

```
ForceSignal:
    country_iso3
    force_code
    scoring_period

    level_score: float | None
    relative_score: float | None
    momentum: float | None
    confidence: float | None

    coverage_status
    coverage_ceiling

    component_signals
    missing_components
    deferred_components

    aggregation_method
    force_model_version
    normalization_model_version

    backtest_safe
```

Requirements:
- component provenance must be preserved
- `None` never zero
- no raw observations directly inside scoring arithmetic
- score fields validated by dimension ranges
- force confidence independent
- coverage independent

No DB table. No persistence. No public API yet.

## 12. What Sprint 5.21 does NOT do

- No force calculation service
- No force level values
- No force relative values
- No force momentum values
- No force confidence
- No force persistence
- No force API
- No phase/stage
- No cycle composites
- No forecasts
- No frontend gauges
- No equal weights
- No Indebtedness aggregation formula
- No government-debt normalization
- No Gini normalization
- No education normalization
- No WID normalization
