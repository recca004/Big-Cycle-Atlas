# United Kingdom (GBR) — economic research profile

Generated: 2026-11-25T22:27:21.020278Z
Methodology: experimental, `normalization-v1.4`, `force-aggregation-v1.0`
Requested calculation period: `2026-Q3`
Latest classified composite period: `2025-Q4`
Latest raw observation period: `2026`

## Current interpretation

The production `model_b_domain` result is **58.25398582045857** with stage **DECLINE**, direction `declining`, and coverage ratio `0.6521739130434783`. This is an experimental domestic-condition cycle result, not an international-power ranking and not a claim about an empire life-cycle stage.

## Composite models

| Model | Period | Score | Stage | Coverage |
|---|---:|---:|---|---:|
| `model_a_equal` | 2025-Q4 | 64.74457428653 | EARLY_DECLINE | 0.6521739130434783 |
| `model_b_domain` | 2025-Q4 | 58.25398582045857 | DECLINE | 0.6521739130434783 |
| `model_c_overlap` | 2025-Q4 | 58.25398582045857 | DECLINE | 0.6521739130434783 |
| `model_d_comparable` | 2025-Q4 | 66.36644103772893 | EARLY_DECLINE | 0.6521739130434783 |

## Seventeen-force evidence

| Force | Status | Level | Coverage | Period | Actual measurement and limitation |
|---|---|---:|---|---|---|
| Leadership capabilities | scored | 77.5838889 | partial | 2026-Q3 | WGI Government Effectiveness (2025 revision, 0-100) is the institutional proxy: quality of public services, civil service, policy formulation and implementation. It measures state capacity, not individual leaders — no subjective leader ratings. Capped PARTIAL: one governance dimension is not the whole leadership-capabilities concept (Sprint 6.21, DEC-041). |
| Education | scored | 61.1865194944378 | partial | 2026-Q3 | Live input: OECD tertiary attainment age 25-34 (ISCED 5-8, % of population, annual, Sprint 5.20). Attainment != enrollment. CHN has only 1 data point (2010); IND has 8 sparse data points. Still missing: secondary attainment/enrollment, learning outcomes/test scores, education quality, years of schooling, skills. One tertiary series cannot make Education AVAILABLE — capped at PARTIAL. |
| Character / determination | scored | 48.62637362637363 | partial | 2026-Q3 | PARTIAL proxy (V1 Mission 1, delegated working model): the executable component measures RELATIVE ECONOMIC PARTICIPATION — labour force participation rate (ILO modeled, ages 15+) scored as a WDI-universe percentile. This is a narrow, labeled proxy for economic participation only; it is NOT a measurement of national character or determination. Resourcefulness, entrepreneurship and innovation dimensions remain unmeasured. PARTIAL ceiling enforced; higher participation is not universally positive (documented limitation). |
| Rule of law | scored | 79.5262725 | available | 2026-Q3 | World Bank WGI Rule of Law governance score (2025 revision, 0-100 absolute scale) live 1996-present for all 8 countries. Perception-based composite with measurement uncertainty; the 90% CI bounds and source counts are stored in the separate indicator_diagnostics evidence path and never become force inputs. This is a SOURCE indicator for the force, not an Atlas force score. |
| Corruption | scored | 78.9181245 | available | 2026-Q3 | Source is WGI 'Control of Corruption' (2025 revision, 0-100): HIGHER means stronger control of corruption / less corruption — the raw stored value is never reversed or reinterpreted. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. This is a SOURCE indicator, not an Atlas force score. |
| Resource allocation efficiency | context_only | — | partial | 2026-Q3 | Investment & resource-allocation CONTEXT profile (Mission 4 §17): investment effort (GCF % of GDP), output growth, and labour productivity describe the input side — none of them measures allocation efficiency itself, and all three overlap productivity / infrastructure inputs by design (documented, not deduplicated). |
| Global openness | context_only | — | partial | 2026-Q3 | Descriptive openness CONTEXT profile (Mission 4 §16): trade intensity (exports+imports % of GDP, exposed as derived TRADE_OPENNESS_GDP), external balance, current account, FDI inflows, plus population/GDP size context as candidates. Trade intensity is NOT strength (DEC-035) and these inputs overlap trade_capital_flows deliberately. The full force (capital, people, ideas) remains unmeasurable — no level score is claimed. |
| Productivity / output growth | scored | 58.57142857142857 | partial | 2026-Q3 | OECD labour productivity per hour (6/8 countries — CHN/IND are not OECD members and cannot receive an OECD-calibrated score). Sprint 6.14 (DEC-042 Option A — owner approved): level = mid-rank percentile within the versioned OECD universe oecd_lpph_v1, period-specific. Capped PARTIAL: OECD relative productivity position only — not the whole productivity/output-growth force, not a global percentile. |
| Cost competitiveness | dimension_only | — | partial | 2026-Q3 | ULC growth is relative-cost meaningful; CPI inflation is a domestic price-pressure input. Relative international competitiveness ultimately needs exchange rates and partner-country price/cost comparisons — CPI alone (e.g. CHN/IND without OECD ULC) makes this force partial, never available. |
| Trade and capital flows | context_only | — | available | 2026-Q3 | World Bank WDI live (2000–2025, all 8 countries): exports/imports of goods and services, the published external balance (direct provider series for trade balance — not derived), and the current account. FDI net inflows (%GDP) live 1990+ all 8 countries (V1 Mission 1). Capital-flow measures beyond the current account and bilateral flows (UN Comtrade) come later. |
| Infrastructure and investment | context_only | — | available | 2026-Q3 | World Bank gross capital formation live (2000–2025, all 8 countries) + fixed broadband per 100 (Mission 2). Investment effort + digital coverage context — NOT infrastructure quality. |
| Indebtedness | scored | 98.62385321100918 | available | 2026-Q3 | Private-sector credit gap + debt service (BIS) + general-government gross debt (IMF WEO, Sprint 5.19). Government debt is a raw level input only — no monotonic 'higher debt = weaker' curve is approved; debt sustainability depends on interest cost, currency, maturity, fiscal capacity, monetary sovereignty, and growth (CONTEXTUAL_DEFERRED in the normalization registry). Sprint 6.13 (DEC-040, ratified) added a score: CONDITION_MINUS_PENALTY composition, level = clamp(DSR + (credit_gap - 50), 0, 100), force-aggregation-v0.4. |
| Military strength | dimension_only | — | partial | 2026-Q3 | Live inputs are spending measures only (World Bank MS.MIL.XPND.CD / MS.MIL.XPND.GD.ZS, underlying source: SIPRI Military Expenditure Database). SIPRI describes military expenditure as an INPUT measure - resources absorbed by the military - not a measure of military capability or security. Personnel capability, equipment quality and quantity, technology, logistics, readiness, combat experience, alliances/force projection, and nuclear capability are not measured, so spending alone can never make this force AVAILABLE (DEC-009 ceiling). |
| Wealth / opportunity / values gaps | scored | 42.86 | partial | 2026-Q3 | Live inputs: World Bank Gini index (income inequality, irregular) + WID top 10% net personal wealth share (wealth concentration, annual, Sprint 5.20). Both are distributional measures — opportunity gaps and values/social polarization remain missing. The force is capped at PARTIAL until its conceptual scope is better covered. WID data_quality column preserved but NOT used for filtering (official semantics unverified). |
| Internal conflict | scored | 70.6839867 | partial | 2026-Q3 | Initial institutional/conflict-risk proxy: WGI 'Political Stability and Absence of Violence/Terrorism' governance score (2025 revision, 0-100) live 1996-2024 for all 8 countries. It does NOT measure every form of domestic conflict (polarization, protests, distributional tension) — the force is capped at PARTIAL while this proxy is the only input; later ACLED / event data may strengthen it. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. SOURCE indicator, not an Atlas force score. |
| Geography | context_only | — | structural_context_available | 2026-Q3 | Structural context profile `geo_profile_v1` (landlocked status, coastline, island status, land area and maritime access) is available for all tracked countries. It is deliberately static context and has no live time-series input or score. |
| Acts of nature | context_only | — | partial | 2026-Q3 | Verified structural exposure context (Mission 4 §18): WB EN.CLC.MDAT.ZS, an EM-DAT-derived % of population affected by droughts/floods/extreme temperatures averaged over 1990-2009 (published at 2009 only — no annual series). Pandemic and climate-change exposure have no legally accessible provider series ingested yet; missing values mean 'not published', never 'zero events'. |

## Historical raw-indicator changes

The `range baseline` is the first observation in the requested 1980-present window; the `full baseline` is the first observation ever stored. These are deliberately separate views.

| Force / indicator | Earliest | Range baseline | Latest | Range baseline value | Latest value | Range change | Full baseline | Full change | Unit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wealth_opportunity_values_gaps `WEALTH_SHARE_TOP_10` | 1820 | 1980 | 2024 | 0.5826 | 0.5714 | -0.011199999999999988 | 1820 | -0.37440000000000007 | share (0-1) |
| cost_competitiveness `INFLATION_CPI` | 1960 | 1980 | 2025 | 17.9659242656857 | 3.88306881625999 | -14.082855449425711 | 1960 | 2.8794931123582703 | percent |
| military_strength `MILITARY_EXPENDITURE_USD` | 1960 | 1980 | 2025 | 28360159219.7249 | 88977496940.3926 | 60617337720.667694 | 1960 | 83847639850.50082 | current US$ |
| military_strength `MILITARY_EXPENDITURE_GDP` | 1960 | 1980 | 2025 | 5.0199034589 | 2.3532641541 | -2.6666393048 | 1960 | -4.7392222167 | percent of GDP |
| resource_allocation_efficiency `GDP_GROWTH` | 1961 | 1980 | 2025 | -2.17910220206564 | 1.38844207858726 | 3.5675442806529 | 1961 | -1.3128721346953098 | percent |
| productivity_output_growth `GDP_GROWTH` | 1961 | 1980 | 2025 | -2.17910220206564 | 1.38844207858726 | 3.5675442806529 | 1961 | -1.3128721346953098 | percent |
| wealth_opportunity_values_gaps `GINI_INDEX` | 1968 | 1980 | 2021 | 28.5 | 32.4 | 3.8999999999999986 | 1968 | 5.599999999999998 | index (0-100) |
| resource_allocation_efficiency `GROSS_CAPITAL_FORMATION_GDP` | 1970 | 1980 | 2025 | 21.8204358753913 | 19.6884002261946 | -2.132035649196702 | 1970 | -5.114619002102401 | percent |
| global_openness `EXPORTS_GDP` | 1970 | 1980 | 2025 | 26.8961069038285 | 30.5969582161816 | 3.7008513123531017 | 1970 | 8.5614786106647 | percent |
| global_openness `IMPORTS_GDP` | 1970 | 1980 | 2025 | 24.4141733546691 | 31.8603712472379 | 7.446197892568801 | 1970 | 10.891542391936799 | percent |
| global_openness `TRADE_BALANCE` | 1970 | 1980 | 2025 | 2.48193354915939 | -1.26341303105635 | -3.74534658021574 | 1970 | -2.3300637812721403 | percent |
| global_openness `CURRENT_ACCOUNT_GDP` | 1970 | 1980 | 2025 | 1.21462434887474 | -3.13347768999639 | -4.348102038871129 | 1970 | -4.64137474293843 | percent |
| global_openness `FDI_NET_INFLOWS_GDP` | 1970 | 1980 | 2025 | 1.79181968888777 | 0.939113289040925 | -0.852706399846845 | 1970 | -0.19961530148778495 | percent of GDP |
| trade_capital_flows `EXPORTS_GDP` | 1970 | 1980 | 2025 | 26.8961069038285 | 30.5969582161816 | 3.7008513123531017 | 1970 | 8.5614786106647 | percent |
| trade_capital_flows `IMPORTS_GDP` | 1970 | 1980 | 2025 | 24.4141733546691 | 31.8603712472379 | 7.446197892568801 | 1970 | 10.891542391936799 | percent |
| trade_capital_flows `TRADE_BALANCE` | 1970 | 1980 | 2025 | 2.48193354915939 | -1.26341303105635 | -3.74534658021574 | 1970 | -2.3300637812721403 | percent |
| trade_capital_flows `CURRENT_ACCOUNT_GDP` | 1970 | 1980 | 2025 | 1.21462434887474 | -3.13347768999639 | -4.348102038871129 | 1970 | -4.64137474293843 | percent |
| trade_capital_flows `FDI_NET_INFLOWS_GDP` | 1970 | 1980 | 2025 | 1.79181968888777 | 0.939113289040925 | -0.852706399846845 | 1970 | -0.19961530148778495 | percent of GDP |
| infrastructure_investment `GROSS_CAPITAL_FORMATION_GDP` | 1970 | 1980 | 2025 | 21.8204358753913 | 19.6884002261946 | -2.132035649196702 | 1970 | -5.114619002102401 | percent |
| indebtedness `CREDIT_TO_GDP_GAP` | 1973 | 1980 | 2026 | -1.2109 | -20.1244 | -18.913500000000003 | 1973 | -22.860200000000003 | percentage of GDP |
| cost_competitiveness `REER_INDEX` | 1979 | 1980 | 2025 | 139.448315088915 | 110.644601526328 | -28.803713562586992 | 1979 | -8.62274322351999 | index |
| resource_allocation_efficiency `LABOUR_PRODUCTIVITY_PER_HOUR` | 1980 | 1980 | 2025 | 36.87529693893627 | 72.74785647399722 | 35.872559535060944 | 1980 | 35.872559535060944 | US dollars per hour, PPP converted |
| productivity_output_growth `LABOUR_PRODUCTIVITY_PER_HOUR` | 1980 | 1980 | 2025 | 36.87529693893627 | 72.74785647399722 | 35.872559535060944 | 1980 | 35.872559535060944 | US dollars per hour, PPP converted |
| indebtedness `GOVERNMENT_DEBT_GDP` | 1980 | 1980 | 2025 | 42.688677 | 102.055709 | 59.367031999999995 | 1980 | 59.367031999999995 | percent |
| character_determination `LABOUR_FORCE_PARTICIPATION_RATE` | 1990 | 1990 | 2025 | 62.376 | 61.369 | -1.006999999999998 | 1990 | -1.006999999999998 | percent |
| cost_competitiveness `UNIT_LABOUR_COST_GROWTH` | 1993 | 1993 | 2026 | -1.055809 | 5.610706 | 6.666515 | 1993 | 6.666515 | percent per annum |
| leadership_capabilities `GOVERNMENT_EFFECTIVENESS_WGI_SCORE` | 1996 | 1996 | 2025 | 87.4399907 | 77.5838889 | -9.85610179999999 | 1996 | -9.85610179999999 | score 0-100 |
| rule_of_law `RULE_OF_LAW_WGI_SCORE` | 1996 | 1996 | 2025 | 85.2427336 | 79.5262725 | -5.716461099999989 | 1996 | -5.716461099999989 | score 0-100 |
| corruption `CONTROL_OF_CORRUPTION_WGI_SCORE` | 1996 | 1996 | 2025 | 89.3449126 | 78.9181245 | -10.426788099999996 | 1996 | -10.426788099999996 | score 0-100 |
| internal_conflict `POLITICAL_STABILITY_WGI_SCORE` | 1996 | 1996 | 2025 | 84.3953337 | 70.6839867 | -13.71134699999999 | 1996 | -13.71134699999999 | score 0-100 |
| education `TERTIARY_ATTAINMENT_25_34` | 1997 | 1997 | 2025 | 24.681225 | 61.1865194944378 | 36.505294494437805 | 1997 | 36.505294494437805 | percent |
| indebtedness `DEBT_SERVICE_RATIO` | 1999 | 1999 | 2026 | 13.9 | 12.9 | -1.0 | 1999 | -1.0 | per cent |
| infrastructure_investment `BROADBAND_PER_100` | 2000 | 2000 | 2024 | 0.0895570335391683 | 42.1648283773461 | 42.07527134380693 | 2000 | 42.07527134380693 | per 100 people |
| acts_of_nature `NATURAL_DISASTER_AFFECTED_PCT` | 2009 | 2009 | 2009 | 0.0324070189450731 | 0.0324070189450731 | 0.0 | 2009 | 0.0 | percent of population |

## Scientific limitations

- Raw history is latest-vintage evidence; it is not a release-date-safe backtest.
- Missing periods remain missing. No value in this report is interpolated.
- Force statuses distinguish scores, dimension-only signals and context profiles.
- Military expenditure is resources, not total capability.
- Tracked-universe shares are not global shares.
