# DEC-040 validation report — Indebtedness CONDITION_MINUS_PENALTY

Generated: retrospective diagnostic run (NOT release-date-safe;
backtest_safe = False everywhere). Model: force-aggregation-v0.4

## 1. Latest snapshot per country

| Country | Period | DSR raw | DSR src | cal n | cal span | stress % | DSR level | gap raw | gap src | gap level | penalty | **force level** | coverage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| USA | 2026-Q3 | 14.10 | 2025-Q4 | 104/20 | 2000-Q1…2025-Q4 | 5.29 | 94.71 | -11.54 | 2025-Q4 | 50.00 | 0.00 | **94.71** | available |
| CHN | 2026-Q3 | 18.80 | 2025-Q4 | 104/20 | 2000-Q1…2025-Q4 | 97.12 | 2.88 | -7.69 | 2025-Q4 | 50.00 | 0.00 | **2.88** | available |
| CHE | 2026-Q3 | 19.70 | 2025-Q4 | 104/20 | 2000-Q1…2025-Q4 | 86.54 | 13.46 | -17.04 | 2025-Q4 | 50.00 | 0.00 | **13.46** | available |
| DEU | 2026-Q3 | 12.20 | 2025-Q4 | 104/20 | 2000-Q1…2025-Q4 | 11.06 | 88.94 | -3.96 | 2025-Q4 | 50.00 | 0.00 | **88.94** | available |
| FRA | 2026-Q3 | 20.80 | 2025-Q4 | 104/20 | 2000-Q1…2025-Q4 | 95.67 | 4.33 | -15.11 | 2025-Q4 | 50.00 | 0.00 | **4.33** | available |
| GBR | 2026-Q3 | 13.10 | 2025-Q4 | 104/20 | 2000-Q1…2025-Q4 | 3.85 | 96.15 | -17.82 | 2025-Q4 | 50.00 | 0.00 | **96.15** | available |
| JPN | 2026-Q3 | 15.50 | 2025-Q4 | 104/20 | 2000-Q1…2025-Q4 | 75.00 | 25.00 | 6.78 | 2025-Q4 | 20.10 | -29.90 | **0.00** | available |
| IND | 2026-Q3 | 12.20 | 2025-Q4 | 104/20 | 2000-Q1…2025-Q4 | 56.25 | 43.75 | 1.74 | 2025-Q4 | 50.00 | 0.00 | **43.75** | available |

Government-debt context (SUPPORTING_CONTEXT, unscored): USA 123.9% (2025); CHN 90.4% (2024); CHE 39.4% (2025); DEU 62.9% (2025); FRA 113.2% (2024); GBR 102.3% (2025); JPN 214.5% (2024); IND 84.1% (2025)

## 2. Switzerland 13.46 — decomposition

- DSR raw 19.7: own-history stress percentile 86.5 → DSR level 13.5 (n=104, span 2000-Q1…2025-Q4).
- Credit gap raw -17.0378 → gap level 50.0 → penalty 0.0.
- Force level = clamp(13.5 + (0.0), 0, 100) = **13.46**.

Driver: **entirely the DSR own-history percentile** — the credit gap is neutral.

## 3. Historical profile — crisis windows

### GFC 2008-2009

| Country | periods scored | min | mean | max | mean DSR | mean penalty |
|---|---|---|---|---|---|---|
| USA | 8/8 | 0.0 | 24.0 | 66.2 | 38.9 | -27.4 |
| CHN | 8/8 | 0.0 | 21.4 | 86.1 | 21.8 | -17.8 |
| CHE | 8/8 | 0.0 | 8.8 | 25.8 | 10.7 | -11.0 |
| DEU | 8/8 | 71.1 | 84.5 | 97.0 | 84.5 | 0.0 |
| FRA | 8/8 | 0.0 | 0.0 | 0.0 | 8.0 | -38.9 |
| GBR | 8/8 | 0.0 | 12.3 | 39.0 | 21.9 | -20.0 |
| JPN | 8/8 | 49.9 | 79.8 | 98.5 | 83.5 | -3.7 |
| IND | 8/8 | 0.0 | 0.0 | 0.0 | 6.5 | -50.0 |

### Eurozone crisis 2010-2013

| Country | periods scored | min | mean | max | mean DSR | mean penalty |
|---|---|---|---|---|---|---|
| USA | 16/16 | 73.2 | 95.2 | 99.1 | 95.2 | 0.0 |
| CHN | 16/16 | 0.0 | 0.0 | 0.0 | 1.2 | -44.8 |
| CHE | 16/16 | 0.0 | 0.0 | 0.0 | 14.5 | -47.0 |
| DEU | 16/16 | 81.2 | 93.9 | 99.0 | 93.9 | 0.0 |
| FRA | 16/16 | 0.0 | 1.1 | 11.0 | 9.1 | -31.3 |
| GBR | 16/16 | 42.4 | 61.9 | 87.5 | 62.2 | -0.2 |
| JPN | 16/16 | 91.5 | 97.3 | 99.1 | 97.6 | -0.3 |
| IND | 16/16 | 0.0 | 4.5 | 22.3 | 11.9 | -17.5 |

### COVID 2020

| Country | periods scored | min | mean | max | mean DSR | mean penalty |
|---|---|---|---|---|---|---|
| USA | 4/4 | 67.9 | 78.8 | 88.0 | 86.8 | -8.0 |
| CHN | 4/4 | 0.2 | 7.6 | 14.2 | 8.2 | -0.6 |
| CHE | 4/4 | 0.0 | 0.0 | 0.0 | 1.2 | -50.0 |
| DEU | 4/4 | 12.7 | 37.5 | 77.2 | 66.9 | -29.4 |
| FRA | 4/4 | 0.0 | 0.0 | 0.0 | 0.9 | -45.3 |
| GBR | 4/4 | 58.9 | 75.6 | 89.5 | 77.8 | -2.2 |
| JPN | 4/4 | 0.0 | 2.8 | 9.9 | 52.2 | -50.0 |
| IND | 4/4 | 63.1 | 65.3 | 69.8 | 65.3 | 0.0 |

### Tightening 2022-2023

| Country | periods scored | min | mean | max | mean DSR | mean penalty |
|---|---|---|---|---|---|---|
| USA | 8/8 | 60.2 | 73.8 | 92.1 | 73.8 | 0.0 |
| CHN | 8/8 | 3.2 | 15.2 | 25.8 | 15.2 | 0.0 |
| CHE | 8/8 | 0.0 | 6.0 | 12.0 | 8.2 | -11.5 |
| DEU | 8/8 | 45.6 | 67.1 | 90.6 | 77.1 | -10.1 |
| FRA | 8/8 | 5.6 | 10.0 | 16.1 | 10.0 | 0.0 |
| GBR | 8/8 | 96.4 | 98.7 | 99.5 | 98.7 | 0.0 |
| JPN | 8/8 | 0.0 | 0.8 | 5.8 | 46.1 | -50.0 |
| IND | 8/8 | 63.0 | 68.7 | 75.0 | 68.7 | 0.0 |

## 4. Sensitivity analysis

- Scored snapshots: 704 of 856 data-bearing snapshots.
- Penalty distribution: min -50.0, max 0.0, mean -14.3; fraction of scored snapshots with penalty < 0 (gap elevated): 40.8%.
- Zero-level snapshots: 209 (29.7%).
- 100-level snapshots: 0.
- Level range: 0.0 … 99.5; DSR-core range: 0.5 … 99.5.
- Compression: corr(force level, DSR core) = 0.959 (1.0 = penalty never moves the score).

### Penalty-strength variants (research-only, production formula unchanged)

| strength s | min | mean | max | zero-share |
|---|---|---|---|---|
| 0.0 | 0.5 | 48.9 | 99.5 | 0.0% |
| 0.5 | 0.0 | 45.4 | 99.5 | 24.0% |
| 1.0 | 0.0 | 43.4 | 99.5 | 29.7% |
| 1.5 | 0.0 | 42.5 | 99.5 | 33.1% |
| 2.0 | 0.0 | 42.0 | 99.5 | 34.7% |

Note: s=0 ignores the gap (DSR-only); s=1 is the DEC-040 formula. Missing components defer at every strength — the missing-never-neutral rule is structural, not parameterized.

## 5. What is inherited vs. what is an Atlas assumption

Inherited from already-approved methods (no new science):
- DSR own-history level: DEC-019 / normalization (min n=20, mid-rank, freshness gates).
- Credit-gap one-sided vulnerability: DEC-021 (neutral 50 ≤ +2pp, linear to 0 at +10pp).
- Component roles (CORE_CONDITION / VULNERABILITY_PENALTY / SUPPORTING_CONTEXT): DEC-029.
- Missing != zero; coverage independent of strength; non-persistence.

New Atlas model assumption introduced by DEC-040:
- The composition operator itself: additive penalty on the 0–100 scale
  (penalty = gap_level − 50, i.e. the one-sided curve mapped to a
  0…−50 subtraction), with hard clamp at 0/100 and the
  all-components-required completeness rule. The SHAPE (additive,
  one-sided, unit strength s=1) is the assumption; alternatives s<1
  or s>1 are evaluated in §4 and remain research-only.

## 6. Per-country scored history summary

| Country | first scored | last scored | n scored | min | mean | max | mean penalty |
|---|---|---|---|---|---|---|---|
| USA | 2004-Q4 | 2026-Q3 | 88 | 0.0 | 67.5 | 99.1 | -9.5 |
| CHN | 2004-Q4 | 2026-Q3 | 88 | 0.0 | 11.9 | 86.1 | -18.2 |
| CHE | 2004-Q4 | 2026-Q3 | 88 | 0.0 | 15.2 | 98.1 | -26.0 |
| DEU | 2004-Q4 | 2026-Q3 | 88 | 5.3 | 84.1 | 99.3 | -4.0 |
| FRA | 2004-Q4 | 2026-Q3 | 88 | 0.0 | 8.9 | 87.5 | -17.7 |
| GBR | 2004-Q4 | 2026-Q3 | 88 | 0.0 | 66.5 | 99.5 | -6.4 |
| JPN | 2004-Q4 | 2026-Q3 | 88 | 0.0 | 60.4 | 99.2 | -17.6 |
| IND | 2004-Q4 | 2026-Q3 | 88 | 0.0 | 32.9 | 75.0 | -15.1 |

## 7. Assessment and recommendation

**Findings.**

1. **CHE 13.46 explained**: entirely the DSR own-history percentile
   (86.5th stress percentile — Swiss DSR 19.7% is high relative to its own
   2000–2025 distribution, consistent with structurally high household
   debt). The credit gap contributes nothing (−17.0pp → neutral 50).
   This is NOT a crisis signal — it is a chronic-condition reading.
2. **Crisis behavior is face-valid**: the floor binds exactly where the
   economics say it should — GFC (USA/CHN/CHE/FRA/GBR/IND at or near 0;
   DEU/JPN stayed high, consistent with their non-boom credit cycles),
   euro crisis (CHN/CHE/FRA at 0), COVID-2020 (CHE/FRA/JPN/DEU penalty
   −50 on the GDP-denominator credit-gap spike), tightening (JPN 0 on a
   still-positive gap; high-DSR CHN/FRA/CHE weak).
3. **Composition properties**: penalty active in 40.8% of scored
   snapshots; corr(force, DSR core) = 0.959 — the force is DSR-led with
   the gap acting as an episodic veto, which matches the intended
   "condition, not second equal input" semantics.
4. **Sensitivity**: zero-share rises smoothly with strength (s=0: 0%,
   s=0.5: 24%, s=1: 29.7%, s=1.5: 33%) — no discontinuity or instability
   in the formula. The 29.7% zero share concentrates in genuine stress
   windows; post-2014 zeros are rare. The floor hides differentiation
   among the worst outcomes — a known limitation of any clamped scale,
   not a defect of this operator.
5. **Robustness**: scored history starts 2004-Q4 everywhere (the
   own-history min-n=20 gate, not data absence); staleness defers cleanly;
   no negative or >100 values observed; 0 × 100-level snapshots.

**Recommendation: RATIFY_DEC_040**, with the following documented
limitations (to be surfaced wherever the score is displayed):

- Low-end compression: scores at 0 cannot distinguish "bad" from
  "worst"; the score should be read together with component signals.
- The force is DSR-led (corr 0.96); the gap is an episodic penalty, not
  an equal input — by design.
- Scores before ~2004 do not exist (own-history min-n gate), not a bug.
- Government debt remains context-only; a sovereign-debt input would
  need its own curve DEC (none is defensible today).
- backtest_safe = False until Milestone 9 release-date discipline.

No production-formula change is recommended. If the owner prefers a
softer penalty, s=0.5 is the only economically defensible alternative
variant and would be a one-line config change requiring its own DEC.
