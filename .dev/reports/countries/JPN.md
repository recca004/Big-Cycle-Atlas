# Japan (JPN) — economic research profile

Generated: 2026-11-26T09:05:19.352324Z
Methodology: experimental, `normalization-v1.4`, `force-aggregation-v1.0`
Requested calculation period: `2026-Q3`
Latest classified composite period: `2025-Q4`
Latest raw observation period: `2026`

## Current interpretation

The production `model_b_domain` result is **54.006300514819** with stage **RISE**, direction `steady`, and coverage ratio `0.6521739130434783`. This is an experimental domestic-condition cycle result, not an international-power ranking and not a claim about an empire life-cycle stage.

## Composite models

| Model | Period | Score | Stage | Coverage |
|---|---:|---:|---|---:|
| `model_a_equal` | 2025-Q4 | 66.95433664696186 | PEAK | 0.6521739130434783 |
| `model_b_domain` | 2025-Q4 | 54.006300514819 | RISE | 0.6521739130434783 |
| `model_c_overlap` | 2025-Q4 | 54.006300514819 | RISE | 0.6521739130434783 |
| `model_d_comparable` | 2025-Q4 | 73.49373737802198 | LATE_RISE | 0.6521739130434783 |

## Seventeen-force evidence

| Force | Status | Level | Coverage | Period | Actual measurement and limitation |
|---|---|---:|---|---|---|
| Leadership capabilities | scored | 94.1244393 | partial | 2026-Q3 | WGI Government Effectiveness (2025 revision, 0-100) is the institutional proxy: quality of public services, civil service, policy formulation and implementation. It measures state capacity, not individual leaders — no subjective leader ratings. Capped PARTIAL: one governance dimension is not the whole leadership-capabilities concept (Sprint 6.21, DEC-041). |
| Education | scored | 67.5294117647059 | partial | 2026-Q3 | Live input: OECD tertiary attainment age 25-34 (ISCED 5-8, % of population, annual, Sprint 5.20). Attainment != enrollment. CHN has only 1 data point (2010); IND has 8 sparse data points. Still missing: secondary attainment/enrollment, learning outcomes/test scores, education quality, years of schooling, skills. One tertiary series cannot make Education AVAILABLE — capped at PARTIAL. |
| Character / determination | scored | 56.86813186813187 | partial | 2026-Q3 | PARTIAL proxy (V1 Mission 1, delegated working model): the executable component measures RELATIVE ECONOMIC PARTICIPATION — labour force participation rate (ILO modeled, ages 15+) scored as a WDI-universe percentile. This is a narrow, labeled proxy for economic participation only; it is NOT a measurement of national character or determination. Resourcefulness, entrepreneurship and innovation dimensions remain unmeasured. PARTIAL ceiling enforced; higher participation is not universally positive (documented limitation). |
| Rule of law | scored | 84.0457499 | available | 2026-Q3 | World Bank WGI Rule of Law governance score (2025 revision, 0-100 absolute scale) live 1996-present for all 8 countries. Perception-based composite with measurement uncertainty; the 90% CI bounds and source counts are stored in the separate indicator_diagnostics evidence path and never become force inputs. This is a SOURCE indicator for the force, not an Atlas force score. |
| Corruption | scored | 77.3824078 | available | 2026-Q3 | Source is WGI 'Control of Corruption' (2025 revision, 0-100): HIGHER means stronger control of corruption / less corruption — the raw stored value is never reversed or reinterpreted. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. This is a SOURCE indicator, not an Atlas force score. |
| Resource allocation efficiency | context_only | — | partial | 2026-Q3 | Investment & resource-allocation CONTEXT profile (Mission 4 §17): investment effort (GCF % of GDP), output growth, and labour productivity describe the input side — none of them measures allocation efficiency itself, and all three overlap productivity / infrastructure inputs by design (documented, not deduplicated). |
| Global openness | context_only | — | partial | 2026-Q3 | Descriptive openness CONTEXT profile (Mission 4 §16): trade intensity (exports+imports % of GDP, exposed as derived TRADE_OPENNESS_GDP), external balance, current account, FDI inflows, plus population/GDP size context as candidates. Trade intensity is NOT strength (DEC-035) and these inputs overlap trade_capital_flows deliberately. The full force (capital, people, ideas) remains unmeasurable — no level score is claimed. |
| Productivity / output growth | scored | 27.142857142857142 | partial | 2026-Q3 | OECD labour productivity per hour (6/8 countries — CHN/IND are not OECD members and cannot receive an OECD-calibrated score). Sprint 6.14 (DEC-042 Option A — owner approved): level = mid-rank percentile within the versioned OECD universe oecd_lpph_v1, period-specific. Capped PARTIAL: OECD relative productivity position only — not the whole productivity/output-growth force, not a global percentile. |
| Cost competitiveness | dimension_only | — | partial | 2026-Q3 | ULC growth is relative-cost meaningful; CPI inflation is a domestic price-pressure input. Relative international competitiveness ultimately needs exchange rates and partner-country price/cost comparisons — CPI alone (e.g. CHN/IND without OECD ULC) makes this force partial, never available. |
| Trade and capital flows | context_only | — | available | 2026-Q3 | World Bank WDI live (2000–2025, all 8 countries): exports/imports of goods and services, the published external balance (direct provider series for trade balance — not derived), and the current account. FDI net inflows (%GDP) live 1990+ all 8 countries (V1 Mission 1). Capital-flow measures beyond the current account and bilateral flows (UN Comtrade) come later. |
| Infrastructure and investment | context_only | — | available | 2026-Q3 | World Bank gross capital formation live (2000–2025, all 8 countries) + fixed broadband per 100 (Mission 2). Investment effort + digital coverage context — NOT infrastructure quality. |
| Indebtedness | scored | 4.584185779816504 | available | 2026-Q3 | Private-sector credit gap + debt service (BIS) + general-government gross debt (IMF WEO, Sprint 5.19). Government debt is a raw level input only — no monotonic 'higher debt = weaker' curve is approved; debt sustainability depends on interest cost, currency, maturity, fiscal capacity, monetary sovereignty, and growth (CONTEXTUAL_DEFERRED in the normalization registry). Sprint 6.13 (DEC-040, ratified) added a score: CONDITION_MINUS_PENALTY composition, level = clamp(DSR + (credit_gap - 50), 0, 100), force-aggregation-v0.4. |
| Military strength | dimension_only | — | partial | 2026-Q3 | Live inputs are spending measures only (World Bank MS.MIL.XPND.CD / MS.MIL.XPND.GD.ZS, underlying source: SIPRI Military Expenditure Database). SIPRI describes military expenditure as an INPUT measure - resources absorbed by the military - not a measure of military capability or security. Personnel capability, equipment quality and quantity, technology, logistics, readiness, combat experience, alliances/force projection, and nuclear capability are not measured, so spending alone can never make this force AVAILABLE (DEC-009 ceiling). |
| Wealth / opportunity / values gaps | scored | 40.879999999999995 | partial | 2026-Q3 | Live inputs: World Bank Gini index (income inequality, irregular) + WID top 10% net personal wealth share (wealth concentration, annual, Sprint 5.20). Both are distributional measures — opportunity gaps and values/social polarization remain missing. The force is capped at PARTIAL until its conceptual scope is better covered. WID data_quality column preserved but NOT used for filtering (official semantics unverified). |
| Internal conflict | scored | 87.6616954 | partial | 2026-Q3 | Initial institutional/conflict-risk proxy: WGI 'Political Stability and Absence of Violence/Terrorism' governance score (2025 revision, 0-100) live 1996-2024 for all 8 countries. It does NOT measure every form of domestic conflict (polarization, protests, distributional tension) — the force is capped at PARTIAL while this proxy is the only input; later ACLED / event data may strengthen it. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. SOURCE indicator, not an Atlas force score. |
| Geography | context_only | — | structural_context_available | 2026-Q3 | Structural context profile `geo_profile_v1` (landlocked status, coastline, island status, land area and maritime access) is available for all tracked countries. It is deliberately static context and has no live time-series input or score. |
| Acts of nature | context_only | — | partial | 2026-Q3 | Verified structural exposure context (Mission 4 §18): WB EN.CLC.MDAT.ZS, an EM-DAT-derived % of population affected by droughts/floods/extreme temperatures averaged over 1990-2009 (published at 2009 only — no annual series). Pandemic and climate-change exposure have no legally accessible provider series ingested yet; missing values mean 'not published', never 'zero events'. |

## Historical raw-indicator changes

The `range baseline` is the first observation in the requested 1980-present window; the `full baseline` is the first observation ever stored. These are deliberately separate views.

| Force / indicator | Earliest | Range baseline | Latest | Range baseline value | Latest value | Range change | Full baseline | Full change | Unit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wealth_opportunity_values_gaps `WEALTH_SHARE_TOP_10` | 1820 | 1980 | 2024 | 0.5716 | 0.5912000000000001 | 0.019600000000000062 | 1820 | -0.08879999999999999 | share (0-1) |
| cost_competitiveness `INFLATION_CPI` | 1960 | 1980 | 2025 | 7.77858176555718 | 3.17253034260247 | -4.60605142295471 | 1960 | -0.40198118275663 | percent |
| military_strength `MILITARY_EXPENDITURE_USD` | 1960 | 1980 | 2025 | 9711741590.62543 | 62158093812.4419 | 52446352221.816475 | 1960 | 61677538256.886345 | current US$ |
| military_strength `MILITARY_EXPENDITURE_GDP` | 1960 | 1980 | 2025 | 0.9067942135 | 1.4116699864 | 0.5048757729 | 1960 | 0.33107509710000005 | percent of GDP |
| resource_allocation_efficiency `GDP_GROWTH` | 1961 | 1980 | 2025 | 2.81759120738283 | 1.19311288444599 | -1.6244783229368402 | 1961 | -10.850423472576011 | percent |
| productivity_output_growth `GDP_GROWTH` | 1961 | 1980 | 2025 | 2.81759120738283 | 1.19311288444599 | -1.6244783229368402 | 1961 | -10.850423472576011 | percent |
| resource_allocation_efficiency `GROSS_CAPITAL_FORMATION_GDP` | 1970 | 1980 | 2024 | 36.6385197813648 | 27.6791711471936 | -8.9593486341712 | 1970 | -16.6594878216359 | percent |
| resource_allocation_efficiency `LABOUR_PRODUCTIVITY_PER_HOUR` | 1970 | 1980 | 2025 | 22.567484158600863 | 53.022775754308675 | 30.455291595707813 | 1970 | 38.161102033586104 | US dollars per hour, PPP converted |
| global_openness `EXPORTS_GDP` | 1970 | 1980 | 2024 | 12.5832408948274 | 21.9799093698461 | 9.396668475018702 | 1970 | 12.048897580113321 | percent |
| global_openness `IMPORTS_GDP` | 1970 | 1980 | 2024 | 13.5165085091259 | 22.8730294879112 | 9.3565209787853 | 1970 | 14.04849747992508 | percent |
| global_openness `TRADE_BALANCE` | 1970 | 1980 | 2024 | -0.933267614298499 | -0.893120118065169 | 0.04014749623333003 | 1970 | -1.9995998998118392 | percent |
| global_openness `FDI_NET_INFLOWS_GDP` | 1970 | 1980 | 2025 | 0.0241076702907454 | 1.03278551644542 | 1.0086778461546746 | 1970 | 0.9904046118983294 | percent of GDP |
| productivity_output_growth `LABOUR_PRODUCTIVITY_PER_HOUR` | 1970 | 1980 | 2025 | 22.567484158600863 | 53.022775754308675 | 30.455291595707813 | 1970 | 38.161102033586104 | US dollars per hour, PPP converted |
| trade_capital_flows `EXPORTS_GDP` | 1970 | 1980 | 2024 | 12.5832408948274 | 21.9799093698461 | 9.396668475018702 | 1970 | 12.048897580113321 | percent |
| trade_capital_flows `IMPORTS_GDP` | 1970 | 1980 | 2024 | 13.5165085091259 | 22.8730294879112 | 9.3565209787853 | 1970 | 14.04849747992508 | percent |
| trade_capital_flows `TRADE_BALANCE` | 1970 | 1980 | 2024 | -0.933267614298499 | -0.893120118065169 | 0.04014749623333003 | 1970 | -1.9995998998118392 | percent |
| trade_capital_flows `FDI_NET_INFLOWS_GDP` | 1970 | 1980 | 2025 | 0.0241076702907454 | 1.03278551644542 | 1.0086778461546746 | 1970 | 0.9904046118983294 | percent of GDP |
| infrastructure_investment `GROSS_CAPITAL_FORMATION_GDP` | 1970 | 1980 | 2024 | 36.6385197813648 | 27.6791711471936 | -8.9593486341712 | 1970 | -16.6594878216359 | percent |
| indebtedness `CREDIT_TO_GDP_GAP` | 1974 | 1980 | 2026 | -2.6749 | 5.6702 | 8.3451 | 1974 | 9.537 | percentage of GDP |
| cost_competitiveness `REER_INDEX` | 1980 | 1980 | 2025 | 73.8413284742669 | 56.0730750544094 | -17.7682534198575 | 1980 | -17.7682534198575 | index |
| indebtedness `GOVERNMENT_DEBT_GDP` | 1980 | 1980 | 2024 | 41.422891 | 213.588773 | 172.165882 | 1980 | 172.165882 | percent |
| cost_competitiveness `UNIT_LABOUR_COST_GROWTH` | 1981 | 1981 | 2026 | 2.9045 | 4.123454 | 1.2189539999999996 | 1981 | 1.2189539999999996 | percent per annum |
| character_determination `LABOUR_FORCE_PARTICIPATION_RATE` | 1990 | 1990 | 2025 | 63.392 | 63.448 | 0.055999999999997385 | 1990 | 0.055999999999997385 | percent |
| leadership_capabilities `GOVERNMENT_EFFECTIVENESS_WGI_SCORE` | 1996 | 1996 | 2025 | 75.5546105 | 94.1244393 | 18.56982880000001 | 1996 | 18.56982880000001 | score 0-100 |
| rule_of_law `RULE_OF_LAW_WGI_SCORE` | 1996 | 1996 | 2025 | 80.8722414 | 84.0457499 | 3.173508500000011 | 1996 | 3.173508500000011 | score 0-100 |
| corruption `CONTROL_OF_CORRUPTION_WGI_SCORE` | 1996 | 1996 | 2025 | 72.3688783 | 77.3824078 | 5.01352949999999 | 1996 | 5.01352949999999 | score 0-100 |
| global_openness `CURRENT_ACCOUNT_GDP` | 1996 | 1996 | 2025 | 1.37399041718279 | 4.86496093471918 | 3.4909705175363905 | 1996 | 3.4909705175363905 | percent |
| trade_capital_flows `CURRENT_ACCOUNT_GDP` | 1996 | 1996 | 2025 | 1.37399041718279 | 4.86496093471918 | 3.4909705175363905 | 1996 | 3.4909705175363905 | percent |
| internal_conflict `POLITICAL_STABILITY_WGI_SCORE` | 1996 | 1996 | 2025 | 89.0233095 | 87.6616954 | -1.361614099999997 | 1996 | -1.361614099999997 | score 0-100 |
| education `TERTIARY_ATTAINMENT_25_34` | 1997 | 1997 | 2025 | 45.744064 | 67.5294117647059 | 21.785347764705897 | 1997 | 21.785347764705897 | percent |
| infrastructure_investment `BROADBAND_PER_100` | 1998 | 1998 | 2023 | 0.025334817 | 38.6312383711286 | 38.6059035541286 | 1998 | 38.6059035541286 | per 100 people |
| indebtedness `DEBT_SERVICE_RATIO` | 1999 | 1999 | 2026 | 20.0 | 15.5 | -4.5 | 1999 | -4.5 | per cent |
| wealth_opportunity_values_gaps `GINI_INDEX` | 2008 | 2008 | 2020 | 34.6 | 32.3 | -2.3000000000000043 | 2008 | -2.3000000000000043 | index (0-100) |
| acts_of_nature `NATURAL_DISASTER_AFFECTED_PCT` | 2009 | 2009 | 2009 | 0.0209515501455421 | 0.0209515501455421 | 0.0 | 2009 | 0.0 | percent of population |

## Scientific limitations

- Raw history is latest-vintage evidence; it is not a release-date-safe backtest.
- Missing periods remain missing. No value in this report is interpolated.
- Force statuses distinguish scores, dimension-only signals and context profiles.
- Military expenditure is resources, not total capability.
- Tracked-universe shares are not global shares.
