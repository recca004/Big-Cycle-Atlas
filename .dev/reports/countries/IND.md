# India (IND) — economic research profile

Generated: 2026-11-25T20:57:36.438304Z  
Methodology: experimental, `normalization-v1.4`, `force-aggregation-v1.0`  
Latest production scoring period: `2026-Q3`

## Current interpretation

The production `model_b_domain` result is **37.90483466981685** with stage **LATE_PEAK**, direction `rising`, and coverage ratio `0.6521739130434783`. This is a domestic-condition research result, not an international-power ranking.

## Composite models

| Model | Period | Score | Stage | Coverage |
|---|---:|---:|---|---:|
| `model_a_equal` | 2025-Q4 | 42.95562893841444 | LATE_PEAK | 0.6521739130434783 |
| `model_b_domain` | 2025-Q4 | 37.90483466981685 | LATE_PEAK | 0.6521739130434783 |
| `model_c_overlap` | 2025-Q4 | 37.90483466981685 | LATE_PEAK | 0.6521739130434783 |
| `model_d_comparable` | 2025-Q4 | 46.264948366483516 | RISE | 0.6521739130434783 |

## Seventeen-force evidence

| Force | Status | Level | Coverage | Period | Actual measurement and limitation |
|---|---|---:|---|---|---|
| Leadership capabilities | scored | 62.6217125 | partial | 2026-Q3 | WGI Government Effectiveness (2025 revision, 0-100) is the institutional proxy: quality of public services, civil service, policy formulation and implementation. It measures state capacity, not individual leaders — no subjective leader ratings. Capped PARTIAL: one governance dimension is not the whole leadership-capabilities concept (Sprint 6.21, DEC-041). |
| Education | scored | 23.09971237 | partial | 2026-Q3 | Live input: OECD tertiary attainment age 25-34 (ISCED 5-8, % of population, annual, Sprint 5.20). Attainment != enrollment. CHN has only 1 data point (2010); IND has 8 sparse data points. Still missing: secondary attainment/enrollment, learning outcomes/test scores, education quality, years of schooling, skills. One tertiary series cannot make Education AVAILABLE — capped at PARTIAL. |
| Character / determination | scored | 26.0989010989011 | partial | 2026-Q3 | PARTIAL proxy (V1 Mission 1, delegated working model): the executable component measures RELATIVE ECONOMIC PARTICIPATION — labour force participation rate (ILO modeled, ages 15+) scored as a WDI-universe percentile. This is a narrow, labeled proxy for economic participation only; it is NOT a measurement of national character or determination. Resourcefulness, entrepreneurship and innovation dimensions remain unmeasured. PARTIAL ceiling enforced; higher participation is not universally positive (documented limitation). |
| Rule of law | scored | 56.5115218 | available | 2026-Q3 | World Bank WGI Rule of Law governance score (2025 revision, 0-100 absolute scale) live 1996-2024 for all 8 countries. Perception-based composite with measurement uncertainty (90% CI bounds and number of sources exist as separate WGI series, not yet imported). This is a SOURCE indicator for the force, not an Atlas force score. |
| Corruption | scored | 42.4113081 | available | 2026-Q3 | Source is WGI 'Control of Corruption' (2025 revision, 0-100): HIGHER means stronger control of corruption / less corruption — the raw stored value is never reversed or reinterpreted. Perception-based composite with measurement uncertainty. This is a SOURCE indicator, not an Atlas force score. |
| Resource allocation efficiency | context_only | — | partial | 2026-Q3 | Investment & resource-allocation CONTEXT profile (Mission 4 §17): investment effort (GCF % of GDP), output growth, and labour productivity describe the input side — none of them measures allocation efficiency itself, and all three overlap productivity / infrastructure inputs by design (documented, not deduplicated). |
| Global openness | context_only | — | partial | 2026-Q3 | Descriptive openness CONTEXT profile (Mission 4 §16): trade intensity (exports+imports % of GDP, exposed as derived TRADE_OPENNESS_GDP), external balance, current account, FDI inflows, plus population/GDP size context as candidates. Trade intensity is NOT strength (DEC-035) and these inputs overlap trade_capital_flows deliberately. The full force (capital, people, ideas) remains unmeasurable — no level score is claimed. |
| Productivity / output growth | context_only | — | partial | 2026-Q3 | OECD labour productivity per hour (6/8 countries — CHN/IND are not OECD members and cannot receive an OECD-calibrated score). Sprint 6.14 (DEC-042 Option A — owner approved): level = mid-rank percentile within the versioned OECD universe oecd_lpph_v1, period-specific. Capped PARTIAL: OECD relative productivity position only — not the whole productivity/output-growth force, not a global percentile. |
| Cost competitiveness | context_only | — | partial | 2026-Q3 | ULC growth is relative-cost meaningful; CPI inflation is a domestic price-pressure input. Relative international competitiveness ultimately needs exchange rates and partner-country price/cost comparisons — CPI alone (e.g. CHN/IND without OECD ULC) makes this force partial, never available. |
| Trade and capital flows | context_only | — | available | 2026-Q3 | World Bank WDI live (2000–2025, all 8 countries): exports/imports of goods and services, the published external balance (direct provider series for trade balance — not derived), and the current account. FDI net inflows (%GDP) live 1990+ all 8 countries (V1 Mission 1). Capital-flow measures beyond the current account and bilateral flows (UN Comtrade) come later. |
| Infrastructure and investment | context_only | — | available | 2026-Q3 | World Bank gross capital formation live (2000–2025, all 8 countries) + fixed broadband per 100 (Mission 2). Investment effort + digital coverage context — NOT infrastructure quality. |
| Indebtedness | scored | 24.475825688073392 | available | 2026-Q3 | Private-sector credit gap + debt service (BIS) + general-government gross debt (IMF WEO, Sprint 5.19). Government debt is a raw level input only — no monotonic 'higher debt = weaker' curve is approved; debt sustainability depends on interest cost, currency, maturity, fiscal capacity, monetary sovereignty, and growth (CONTEXTUAL_DEFERRED in the normalization registry). Sprint 6.13 (DEC-040, ratified) added a score: CONDITION_MINUS_PENALTY composition, level = clamp(DSR + (credit_gap - 50), 0, 100), force-aggregation-v0.4. |
| Military strength | dimension_only | — | partial | 2026-Q3 | Live inputs are spending measures only (World Bank MS.MIL.XPND.CD / MS.MIL.XPND.GD.ZS, underlying source: SIPRI Military Expenditure Database). SIPRI describes military expenditure as an INPUT measure - resources absorbed by the military - not a measure of military capability or security. Personnel capability, equipment quality and quantity, technology, logistics, readiness, combat experience, alliances/force projection, and nuclear capability are not measured, so spending alone can never make this force AVAILABLE (DEC-009 ceiling). |
| Wealth / opportunity / values gaps | scored | 34.99 | partial | 2026-Q3 | Live inputs: World Bank Gini index (income inequality, irregular) + WID top 10% net personal wealth share (wealth concentration, annual, Sprint 5.20). Both are distributional measures — opportunity gaps and values/social polarization remain missing. The force is capped at PARTIAL until its conceptual scope is better covered. WID data_quality column preserved but NOT used for filtering (official semantics unverified). |
| Internal conflict | scored | 54.9562467 | partial | 2026-Q3 | Initial institutional/conflict-risk proxy: WGI 'Political Stability and Absence of Violence/Terrorism' governance score (2025 revision, 0-100) live 1996-2024 for all 8 countries. It does NOT measure every form of domestic conflict (polarization, protests, distributional tension) — the force is capped at PARTIAL while this proxy is the only input; later ACLED / event data may strengthen it. Perception-based composite with measurement uncertainty. SOURCE indicator, not an Atlas force score. |
| Geography | context_only | — | missing | 2026-Q3 | Mostly static; no time-series catalog indicator planned. |
| Acts of nature | context_only | — | partial | 2026-Q3 | Verified structural exposure context (Mission 4 §18): WB EN.CLC.MDAT.ZS, an EM-DAT-derived % of population affected by droughts/floods/extreme temperatures averaged over 1990-2009 (published at 2009 only — no annual series). Pandemic and climate-change exposure have no legally accessible provider series ingested yet; missing values mean 'not published', never 'zero events'. |

## Historical raw-indicator changes

| Force / indicator | Earliest | Latest | Baseline value | Latest value | Change | Unit |
|---|---:|---:|---:|---:|---:|---|
| wealth_opportunity_values_gaps `WEALTH_SHARE_TOP_10` | 1820 | 2024 | 0.4507 | 0.6501 | 0.19940000000000002 | share (0-1) |
| resource_allocation_efficiency `GROSS_CAPITAL_FORMATION_GDP` | 1960 | 2025 | 19.5550034544046 | 34.6030048968457 | 15.048001442441098 | percent |
| global_openness `EXPORTS_GDP` | 1960 | 2025 | 6.13955113216183 | 22.2630410669804 | 16.12348993481857 | percent |
| global_openness `IMPORTS_GDP` | 1960 | 2025 | 9.24502571634426 | 24.0051596190103 | 14.76013390266604 | percent |
| global_openness `TRADE_BALANCE` | 1960 | 2025 | -3.10547458418242 | -1.74211855202993 | 1.3633560321524898 | percent |
| cost_competitiveness `INFLATION_CPI` | 1960 | 2025 | 11.3460734795095 | 2.39884954182294 | -8.947223937686559 | percent |
| trade_capital_flows `EXPORTS_GDP` | 1960 | 2025 | 6.13955113216183 | 22.2630410669804 | 16.12348993481857 | percent |
| trade_capital_flows `IMPORTS_GDP` | 1960 | 2025 | 9.24502571634426 | 24.0051596190103 | 14.76013390266604 | percent |
| trade_capital_flows `TRADE_BALANCE` | 1960 | 2025 | -3.10547458418242 | -1.74211855202993 | 1.3633560321524898 | percent |
| infrastructure_investment `GROSS_CAPITAL_FORMATION_GDP` | 1960 | 2025 | 19.5550034544046 | 34.6030048968457 | 15.048001442441098 | percent |
| military_strength `MILITARY_EXPENDITURE_USD` | 1960 | 2025 | 5420809519.08574 | 92057013588.1601 | 86636204069.07436 | current US$ |
| military_strength `MILITARY_EXPENDITURE_GDP` | 1960 | 2025 | 3.1337813297 | 2.2951791794 | -0.8386021503000003 | percent of GDP |
| resource_allocation_efficiency `GDP_GROWTH` | 1961 | 2025 | 6.7358215279985 | 7.56666179284244 | 0.8308402648439399 | percent |
| productivity_output_growth `GDP_GROWTH` | 1961 | 2025 | 6.7358215279985 | 7.56666179284244 | 0.8308402648439399 | percent |
| indebtedness `CREDIT_TO_GDP_GAP` | 1961 | 2026 | 5.6284 | 4.3224 | -1.306 | percentage of GDP |
| global_openness `FDI_NET_INFLOWS_GDP` | 1970 | 2025 | 0.0424840892344642 | 1.03111732367627 | 0.9886332344418058 | percent of GDP |
| trade_capital_flows `FDI_NET_INFLOWS_GDP` | 1970 | 2025 | 0.0424840892344642 | 1.03111732367627 | 0.9886332344418058 | percent of GDP |
| global_openness `CURRENT_ACCOUNT_GDP` | 1975 | 2025 | -0.958052563978002 | -0.511308076227287 | 0.44674448775071496 | percent |
| trade_capital_flows `CURRENT_ACCOUNT_GDP` | 1975 | 2025 | -0.958052563978002 | -0.511308076227287 | 0.44674448775071496 | percent |
| wealth_opportunity_values_gaps `GINI_INDEX` | 1977 | 2023 | 29.7 | 23.0 | -6.699999999999999 | index (0-100) |
| character_determination `LABOUR_FORCE_PARTICIPATION_RATE` | 1990 | 2025 | — | 55.658 | — | percent |
| indebtedness `GOVERNMENT_DEBT_GDP` | 1991 | 2025 | — | 84.260729 | — | percent |
| leadership_capabilities `GOVERNMENT_EFFECTIVENESS_WGI_SCORE` | 1996 | 2025 | — | 62.6217125 | — | score 0-100 |
| rule_of_law `RULE_OF_LAW_WGI_SCORE` | 1996 | 2025 | — | 56.5115218 | — | score 0-100 |
| corruption `CONTROL_OF_CORRUPTION_WGI_SCORE` | 1996 | 2025 | — | 42.4113081 | — | score 0-100 |
| internal_conflict `POLITICAL_STABILITY_WGI_SCORE` | 1996 | 2025 | — | 54.9562467 | — | score 0-100 |
| indebtedness `DEBT_SERVICE_RATIO` | 1999 | 2026 | — | 12.5 | — | per cent |
| infrastructure_investment `BROADBAND_PER_100` | 2001 | 2024 | — | 3.15046250037677 | — | per 100 people |
| acts_of_nature `NATURAL_DISASTER_AFFECTED_PCT` | 2009 | 2009 | — | 4.3561089920649 | — | percent of population |
| education `TERTIARY_ATTAINMENT_25_34` | 2011 | 2023 | — | 23.09971237 | — | percent |
| resource_allocation_efficiency `LABOUR_PRODUCTIVITY_PER_HOUR` | — | — | — | — | — |  |
| productivity_output_growth `LABOUR_PRODUCTIVITY_PER_HOUR` | — | — | — | — | — |  |
| cost_competitiveness `REER_INDEX` | — | — | — | — | — |  |
| cost_competitiveness `UNIT_LABOUR_COST_GROWTH` | — | — | — | — | — |  |

## Scientific limitations

- Raw history is latest-vintage evidence; it is not a release-date-safe backtest.
- Missing periods remain missing. No value in this report is interpolated.
- Force statuses distinguish scores, dimension-only signals and context profiles.
- Military expenditure is resources, not total capability.
- Tracked-universe shares are not global shares.
