# France (FRA) — economic research profile

Generated: 2026-11-26T09:57:59.064572Z
Methodology: experimental, `normalization-v1.4`, `force-aggregation-v1.0`
Requested calculation period: `2026-Q3`
Latest classified composite period: `2025-Q4`
Latest raw observation period: `2026`

## Current interpretation

The production `model_b_domain` result is **54.96340154911505** with stage **DECLINE**, direction `declining`, and coverage ratio `0.6739130434782609`. This is an experimental domestic-condition cycle result, not an international-power ranking and not a claim about an empire life-cycle stage.

## Composite models

| Model | Period | Score | Stage | Coverage |
|---|---:|---:|---|---:|
| `model_a_equal` | 2025-Q4 | 59.6078196750079 | DECLINE | 0.6739130434782609 |
| `model_b_domain` | 2025-Q4 | 54.96340154911505 | DECLINE | 0.6739130434782609 |
| `model_c_overlap` | 2025-Q4 | 54.96340154911505 | DECLINE | 0.6739130434782609 |
| `model_d_comparable` | 2025-Q4 | 58.992734049999996 | DECLINE | 0.6521739130434783 |

## Seventeen-force evidence

| Force | Status | Level | Coverage | Period | Actual measurement and limitation |
|---|---|---:|---|---|---|
| Leadership capabilities | scored | 77.1399234 | partial | 2026-Q3 | WGI Government Effectiveness (2025 revision, 0-100) is the institutional proxy: quality of public services, civil service, policy formulation and implementation. It measures state capacity, not individual leaders — no subjective leader ratings. Capped PARTIAL: one governance dimension is not the whole leadership-capabilities concept (Sprint 6.21, DEC-041). |
| Education | scored | 55.7632959572061 | partial | 2026-Q3 | Live input: OECD tertiary attainment age 25-34 (ISCED 5-8, % of population, annual, Sprint 5.20). Attainment != enrollment. CHN has only 1 data point (2010); IND has 8 sparse data points. Still missing: secondary attainment/enrollment, learning outcomes/test scores, education quality, years of schooling, skills. One tertiary series cannot make Education AVAILABLE — capped at PARTIAL. |
| Character / determination | scored | 25.0 | partial | 2026-Q3 | PARTIAL proxy (V1 Mission 1, delegated working model): the executable component measures RELATIVE ECONOMIC PARTICIPATION — labour force participation rate (ILO modeled, ages 15+) scored as a WDI-universe percentile. This is a narrow, labeled proxy for economic participation only; it is NOT a measurement of national character or determination. Resourcefulness, entrepreneurship and innovation dimensions remain unmeasured. PARTIAL ceiling enforced; higher participation is not universally positive (documented limitation). |
| Rule of law | scored | 74.6126471 | available | 2026-Q3 | World Bank WGI Rule of Law governance score (2025 revision, 0-100 absolute scale) live 1996-present for all 8 countries. Perception-based composite with measurement uncertainty; the 90% CI bounds and source counts are stored in the separate indicator_diagnostics evidence path and never become force inputs. This is a SOURCE indicator for the force, not an Atlas force score. |
| Corruption | scored | 73.0920335 | available | 2026-Q3 | Source is WGI 'Control of Corruption' (2025 revision, 0-100): HIGHER means stronger control of corruption / less corruption — the raw stored value is never reversed or reinterpreted. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. This is a SOURCE indicator, not an Atlas force score. |
| Resource allocation efficiency | context_only | — | partial | 2026-Q3 | Investment & resource-allocation CONTEXT profile (Mission 4 §17): investment effort (GCF % of GDP), output growth, and labour productivity describe the input side — none of them measures allocation efficiency itself, and all three overlap productivity / infrastructure inputs by design (documented, not deduplicated). |
| Global openness | context_only | — | partial | 2026-Q3 | Descriptive openness CONTEXT profile (Mission 4 §16): trade intensity (exports+imports % of GDP, exposed as derived TRADE_OPENNESS_GDP), external balance, current account, FDI inflows, plus population/GDP size context as candidates. Trade intensity is NOT strength (DEC-035) and these inputs overlap trade_capital_flows deliberately. The full force (capital, people, ideas) remains unmeasurable — no level score is claimed. |
| Productivity / output growth | scored | 67.14285714285714 | partial | 2026-Q3 | OECD labour productivity per hour (6/8 countries — CHN/IND are not OECD members and cannot receive an OECD-calibrated score). Sprint 6.14 (DEC-042 Option A — owner approved): level = mid-rank percentile within the versioned OECD universe oecd_lpph_v1, period-specific. Capped PARTIAL: OECD relative productivity position only — not the whole productivity/output-growth force, not a global percentile. |
| Cost competitiveness | dimension_only | — | partial | 2026-Q3 | ULC growth is relative-cost meaningful; CPI inflation is a domestic price-pressure input. Relative international competitiveness ultimately needs exchange rates and partner-country price/cost comparisons — CPI alone (e.g. CHN/IND without OECD ULC) makes this force partial, never available. |
| Trade and capital flows | context_only | — | available | 2026-Q3 | World Bank WDI live (2000–2025, all 8 countries): exports/imports of goods and services, the published external balance (direct provider series for trade balance — not derived), and the current account. FDI net inflows (%GDP) live 1990+ all 8 countries (V1 Mission 1). Capital-flow measures beyond the current account and bilateral flows (UN Comtrade) come later. |
| Infrastructure and investment | context_only | — | available | 2026-Q3 | World Bank gross capital formation live (2000–2025, all 8 countries) + fixed broadband per 100 (Mission 2). Investment effort + digital coverage context — NOT infrastructure quality. |
| Indebtedness | scored | 11.467889908256879 | available | 2026-Q3 | Private-sector credit gap + debt service (BIS) + general-government gross debt (IMF WEO, Sprint 5.19). Government debt is a raw level input only — no monotonic 'higher debt = weaker' curve is approved; debt sustainability depends on interest cost, currency, maturity, fiscal capacity, monetary sovereignty, and growth (CONTEXTUAL_DEFERRED in the normalization registry). Sprint 6.13 (DEC-040, ratified) added a score: CONDITION_MINUS_PENALTY composition, level = clamp(DSR + (credit_gap - 50), 0, 100), force-aggregation-v0.4. |
| Military strength | dimension_only | — | partial | 2026-Q3 | Live inputs are spending measures only (World Bank MS.MIL.XPND.CD / MS.MIL.XPND.GD.ZS, underlying source: SIPRI Military Expenditure Database). SIPRI describes military expenditure as an INPUT measure - resources absorbed by the military - not a measure of military capability or security. Personnel capability, equipment quality and quantity, technology, logistics, readiness, combat experience, alliances/force projection, and nuclear capability are not measured, so spending alone can never make this force AVAILABLE (DEC-009 ceiling). |
| Wealth / opportunity / values gaps | scored | 40.12 | partial | 2026-Q3 | Live inputs: World Bank Gini index (income inequality, irregular) + WID top 10% net personal wealth share (wealth concentration, annual, Sprint 5.20). Both are distributional measures — opportunity gaps and values/social polarization remain missing. The force is capped at PARTIAL until its conceptual scope is better covered. WID data_quality column preserved but NOT used for filtering (official semantics unverified). |
| Internal conflict | scored | 63.9918003 | partial | 2026-Q3 | Initial institutional/conflict-risk proxy: WGI 'Political Stability and Absence of Violence/Terrorism' governance score (2025 revision, 0-100) live 1996-2024 for all 8 countries. It does NOT measure every form of domestic conflict (polarization, protests, distributional tension) — the force is capped at PARTIAL while this proxy is the only input; later ACLED / event data may strengthen it. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. SOURCE indicator, not an Atlas force score. |
| Geography | context_only | — | structural_context_available | 2026-Q3 | Structural context profile `geo_profile_v1` (landlocked status, coastline, island status, land area and maritime access) is available for all tracked countries. It is deliberately static context and has no live time-series input or score. |
| Acts of nature | context_only | — | partial | 2026-Q3 | Verified structural exposure context (Mission 4 §18): WB EN.CLC.MDAT.ZS, an EM-DAT-derived % of population affected by droughts/floods/extreme temperatures averaged over 1990-2009 (published at 2009 only — no annual series). Pandemic and climate-change exposure have no legally accessible provider series ingested yet; missing values mean 'not published', never 'zero events'. |

## Historical raw-indicator changes

The `range baseline` is the first observation in the requested 1980-present window; the `full baseline` is the first observation ever stored. These are deliberately separate views.

| Force / indicator | Earliest | Range baseline | Latest | Range baseline value | Latest value | Range change | Full baseline | Full change | Unit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wealth_opportunity_values_gaps `WEALTH_SHARE_TOP_10` | 1800 | 1980 | 2024 | 0.5155000000000001 | 0.5988 | 0.08329999999999993 | 1800 | -0.22020000000000006 | share (0-1) |
| cost_competitiveness `UNIT_LABOUR_COST_GROWTH` | 1950 | 1980 | 2026 | 4.175277 | 1.646091 | -2.529186 | 1950 | 1.0028408 | percent per annum |
| resource_allocation_efficiency `GROSS_CAPITAL_FORMATION_GDP` | 1960 | 1980 | 2025 | 26.1163834885544 | 21.9383964560126 | -4.1779870325418 | 1960 | -3.967014889908299 | percent |
| global_openness `EXPORTS_GDP` | 1960 | 1980 | 2025 | 21.9991162581018 | 33.3928225145364 | 11.393706256434598 | 1960 | 17.791591639736097 | percent |
| global_openness `IMPORTS_GDP` | 1960 | 1980 | 2025 | 23.2435741526281 | 33.7995547693485 | 10.555980616720397 | 1960 | 20.959000232373995 | percent |
| global_openness `TRADE_BALANCE` | 1960 | 1980 | 2025 | -1.24445789452628 | -0.406732254812056 | 0.8377256397142241 | 1960 | -3.167408592637866 | percent |
| cost_competitiveness `INFLATION_CPI` | 1960 | 1980 | 2025 | 13.5625803959777 | 0.943824761520197 | -12.618755634457502 | 1960 | -3.1961148416300227 | percent |
| trade_capital_flows `EXPORTS_GDP` | 1960 | 1980 | 2025 | 21.9991162581018 | 33.3928225145364 | 11.393706256434598 | 1960 | 17.791591639736097 | percent |
| trade_capital_flows `IMPORTS_GDP` | 1960 | 1980 | 2025 | 23.2435741526281 | 33.7995547693485 | 10.555980616720397 | 1960 | 20.959000232373995 | percent |
| trade_capital_flows `TRADE_BALANCE` | 1960 | 1980 | 2025 | -1.24445789452628 | -0.406732254812056 | 0.8377256397142241 | 1960 | -3.167408592637866 | percent |
| infrastructure_investment `GROSS_CAPITAL_FORMATION_GDP` | 1960 | 1980 | 2025 | 26.1163834885544 | 21.9383964560126 | -4.1779870325418 | 1960 | -3.967014889908299 | percent |
| military_strength `MILITARY_EXPENDITURE_USD` | 1960 | 1980 | 2025 | 22198183002.4185 | 68007580714.3018 | 45809397711.8833 | 1960 | 64747452722.09648 | current US$ |
| military_strength `MILITARY_EXPENDITURE_GDP` | 1960 | 1980 | 2025 | 3.1552050849 | 2.0266296921 | -1.1285753927999997 | 1960 | -3.4018561927999995 | percent of GDP |
| resource_allocation_efficiency `GDP_GROWTH` | 1961 | 1980 | 2025 | 1.67641337198611 | 0.840949955479587 | -0.8354634165065231 | 1961 | -4.105475504323963 | percent |
| productivity_output_growth `GDP_GROWTH` | 1961 | 1980 | 2025 | 1.67641337198611 | 0.840949955479587 | -0.8354634165065231 | 1961 | -4.105475504323963 | percent |
| resource_allocation_efficiency `LABOUR_PRODUCTIVITY_PER_HOUR` | 1970 | 1980 | 2025 | 43.84419124332898 | 83.10261007795228 | 39.2584188346233 | 1970 | 53.46035518649177 | US dollars per hour, PPP converted |
| global_openness `FDI_NET_INFLOWS_GDP` | 1970 | 1980 | 2025 | 0.472661675842858 | 1.81489710678777 | 1.3422354309449118 | 1970 | 1.393200878408193 | percent of GDP |
| productivity_output_growth `LABOUR_PRODUCTIVITY_PER_HOUR` | 1970 | 1980 | 2025 | 43.84419124332898 | 83.10261007795228 | 39.2584188346233 | 1970 | 53.46035518649177 | US dollars per hour, PPP converted |
| trade_capital_flows `FDI_NET_INFLOWS_GDP` | 1970 | 1980 | 2025 | 0.472661675842858 | 1.81489710678777 | 1.3422354309449118 | 1970 | 1.393200878408193 | percent of GDP |
| wealth_opportunity_values_gaps `GINI_INDEX` | 1970 | 1984 | 2023 | 33.4 | 31.8 | -1.5999999999999979 | 1970 | -5.300000000000001 | index (0-100) |
| global_openness `CURRENT_ACCOUNT_GDP` | 1975 | 1980 | 2025 | -0.605927092588722 | -0.331289693053725 | 0.274637399534997 | 1975 | -1.098200625973099 | percent |
| trade_capital_flows `CURRENT_ACCOUNT_GDP` | 1975 | 1980 | 2025 | -0.605927092588722 | -0.331289693053725 | 0.274637399534997 | 1975 | -1.098200625973099 | percent |
| indebtedness `CREDIT_TO_GDP_GAP` | 1979 | 1980 | 2026 | -7.0624 | -15.741 | -8.6786 | 1979 | -10.6669 | percentage of GDP |
| cost_competitiveness `REER_INDEX` | 1980 | 1980 | 2025 | 118.902380523029 | 91.934128368136 | -26.968252154892994 | 1980 | -26.968252154892994 | index |
| indebtedness `GOVERNMENT_DEBT_GDP` | 1980 | 1980 | 2025 | 21.300088 | 115.534073 | 94.233985 | 1980 | 94.233985 | percent |
| education `TERTIARY_ATTAINMENT_25_34` | 1981 | 1981 | 2025 | 15.120114 | 55.7632959572061 | 40.643181957206096 | 1981 | 40.643181957206096 | percent |
| character_determination `LABOUR_FORCE_PARTICIPATION_RATE` | 1990 | 1990 | 2025 | 55.603 | 55.346 | -0.257000000000005 | 1990 | -0.257000000000005 | percent |
| leadership_capabilities `GOVERNMENT_EFFECTIVENESS_WGI_SCORE` | 1996 | 1996 | 2025 | 84.5048181 | 77.1399234 | -7.364894699999994 | 1996 | -7.364894699999994 | score 0-100 |
| rule_of_law `RULE_OF_LAW_WGI_SCORE` | 1996 | 1996 | 2025 | 82.2845218 | 74.6126471 | -7.671874699999989 | 1996 | -7.671874699999989 | score 0-100 |
| corruption `CONTROL_OF_CORRUPTION_WGI_SCORE` | 1996 | 1996 | 2025 | 76.4377652 | 73.0920335 | -3.3457317000000018 | 1996 | -3.3457317000000018 | score 0-100 |
| internal_conflict `POLITICAL_STABILITY_WGI_SCORE` | 1996 | 1996 | 2025 | 80.5227255 | 63.9918003 | -16.530925200000006 | 1996 | -16.530925200000006 | score 0-100 |
| infrastructure_investment `BROADBAND_PER_100` | 1998 | 1998 | 2024 | 0.023181681 | 48.9251978969333 | 48.9020162159333 | 1998 | 48.9020162159333 | per 100 people |
| indebtedness `DEBT_SERVICE_RATIO` | 1999 | 1999 | 2026 | 15.2 | 19.9 | 4.699999999999999 | 1999 | 4.699999999999999 | per cent |
| acts_of_nature `NATURAL_DISASTER_AFFECTED_PCT` | 2009 | 2009 | 2009 | 0.00571764592926749 | 0.00571764592926749 | 0.0 | 2009 | 0.0 | percent of population |

## Scientific limitations

- Raw history is latest-vintage evidence; it is not a release-date-safe backtest.
- Missing periods remain missing. No value in this report is interpolated.
- Force statuses distinguish scores, dimension-only signals and context profiles.
- Military expenditure is resources, not total capability.
- Tracked-universe shares are not global shares.
