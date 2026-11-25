# China (CHN) — economic research profile

Generated: 2026-11-25T22:27:21.020278Z
Methodology: experimental, `normalization-v1.4`, `force-aggregation-v1.0`
Requested calculation period: `2026-Q3`
Latest classified composite period: `2025-Q4`
Latest raw observation period: `2026`

## Current interpretation

The production `model_b_domain` result is **51.149466187179485** with stage **DECLINE**, direction `declining`, and coverage ratio `0.6521739130434783`. This is an experimental domestic-condition cycle result, not an international-power ranking and not a claim about an empire life-cycle stage.

## Composite models

| Model | Period | Score | Stage | Coverage |
|---|---:|---:|---|---:|
| `model_a_equal` | 2025-Q4 | 54.59316314358974 | LATE_PEAK | 0.6521739130434783 |
| `model_b_domain` | 2025-Q4 | 51.149466187179485 | DECLINE | 0.6521739130434783 |
| `model_c_overlap` | 2025-Q4 | 51.149466187179485 | DECLINE | 0.6521739130434783 |
| `model_d_comparable` | 2025-Q4 | 54.59316314358974 | LATE_PEAK | 0.6521739130434783 |

## Seventeen-force evidence

| Force | Status | Level | Coverage | Period | Actual measurement and limitation |
|---|---|---:|---|---|---|
| Leadership capabilities | scored | 65.1127866 | partial | 2026-Q3 | WGI Government Effectiveness (2025 revision, 0-100) is the institutional proxy: quality of public services, civil service, policy formulation and implementation. It measures state capacity, not individual leaders — no subjective leader ratings. Capped PARTIAL: one governance dimension is not the whole leadership-capabilities concept (Sprint 6.21, DEC-041). |
| Education | context_only | — | partial | 2026-Q3 | Live input: OECD tertiary attainment age 25-34 (ISCED 5-8, % of population, annual, Sprint 5.20). Attainment != enrollment. CHN has only 1 data point (2010); IND has 8 sparse data points. Still missing: secondary attainment/enrollment, learning outcomes/test scores, education quality, years of schooling, skills. One tertiary series cannot make Education AVAILABLE — capped at PARTIAL. |
| Character / determination | scored | 63.46153846153846 | partial | 2026-Q3 | PARTIAL proxy (V1 Mission 1, delegated working model): the executable component measures RELATIVE ECONOMIC PARTICIPATION — labour force participation rate (ILO modeled, ages 15+) scored as a WDI-universe percentile. This is a narrow, labeled proxy for economic participation only; it is NOT a measurement of national character or determination. Resourcefulness, entrepreneurship and innovation dimensions remain unmeasured. PARTIAL ceiling enforced; higher participation is not universally positive (documented limitation). |
| Rule of law | scored | 51.5591046 | available | 2026-Q3 | World Bank WGI Rule of Law governance score (2025 revision, 0-100 absolute scale) live 1996-present for all 8 countries. Perception-based composite with measurement uncertainty; the 90% CI bounds and source counts are stored in the separate indicator_diagnostics evidence path and never become force inputs. This is a SOURCE indicator for the force, not an Atlas force score. |
| Corruption | scored | 49.4738147 | available | 2026-Q3 | Source is WGI 'Control of Corruption' (2025 revision, 0-100): HIGHER means stronger control of corruption / less corruption — the raw stored value is never reversed or reinterpreted. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. This is a SOURCE indicator, not an Atlas force score. |
| Resource allocation efficiency | context_only | — | partial | 2026-Q3 | Investment & resource-allocation CONTEXT profile (Mission 4 §17): investment effort (GCF % of GDP), output growth, and labour productivity describe the input side — none of them measures allocation efficiency itself, and all three overlap productivity / infrastructure inputs by design (documented, not deduplicated). |
| Global openness | context_only | — | partial | 2026-Q3 | Descriptive openness CONTEXT profile (Mission 4 §16): trade intensity (exports+imports % of GDP, exposed as derived TRADE_OPENNESS_GDP), external balance, current account, FDI inflows, plus population/GDP size context as candidates. Trade intensity is NOT strength (DEC-035) and these inputs overlap trade_capital_flows deliberately. The full force (capital, people, ideas) remains unmeasurable — no level score is claimed. |
| Productivity / output growth | context_only | — | partial | 2026-Q3 | OECD labour productivity per hour (6/8 countries — CHN/IND are not OECD members and cannot receive an OECD-calibrated score). Sprint 6.14 (DEC-042 Option A — owner approved): level = mid-rank percentile within the versioned OECD universe oecd_lpph_v1, period-specific. Capped PARTIAL: OECD relative productivity position only — not the whole productivity/output-growth force, not a global percentile. |
| Cost competitiveness | dimension_only | — | partial | 2026-Q3 | ULC growth is relative-cost meaningful; CPI inflation is a domestic price-pressure input. Relative international competitiveness ultimately needs exchange rates and partner-country price/cost comparisons — CPI alone (e.g. CHN/IND without OECD ULC) makes this force partial, never available. |
| Trade and capital flows | context_only | — | available | 2026-Q3 | World Bank WDI live (2000–2025, all 8 countries): exports/imports of goods and services, the published external balance (direct provider series for trade balance — not derived), and the current account. FDI net inflows (%GDP) live 1990+ all 8 countries (V1 Mission 1). Capital-flow measures beyond the current account and bilateral flows (UN Comtrade) come later. |
| Infrastructure and investment | context_only | — | available | 2026-Q3 | World Bank gross capital formation live (2000–2025, all 8 countries) + fixed broadband per 100 (Mission 2). Investment effort + digital coverage context — NOT infrastructure quality. |
| Indebtedness | scored | 0.45871559633027914 | available | 2026-Q3 | Private-sector credit gap + debt service (BIS) + general-government gross debt (IMF WEO, Sprint 5.19). Government debt is a raw level input only — no monotonic 'higher debt = weaker' curve is approved; debt sustainability depends on interest cost, currency, maturity, fiscal capacity, monetary sovereignty, and growth (CONTEXTUAL_DEFERRED in the normalization registry). Sprint 6.13 (DEC-040, ratified) added a score: CONDITION_MINUS_PENALTY composition, level = clamp(DSR + (credit_gap - 50), 0, 100), force-aggregation-v0.4. |
| Military strength | dimension_only | — | partial | 2026-Q3 | Live inputs are spending measures only (World Bank MS.MIL.XPND.CD / MS.MIL.XPND.GD.ZS, underlying source: SIPRI Military Expenditure Database). SIPRI describes military expenditure as an INPUT measure - resources absorbed by the military - not a measure of military capability or security. Personnel capability, equipment quality and quantity, technology, logistics, readiness, combat experience, alliances/force projection, and nuclear capability are not measured, so spending alone can never make this force AVAILABLE (DEC-009 ceiling). |
| Wealth / opportunity / values gaps | scored | 31.95 | partial | 2026-Q3 | Live inputs: World Bank Gini index (income inequality, irregular) + WID top 10% net personal wealth share (wealth concentration, annual, Sprint 5.20). Both are distributional measures — opportunity gaps and values/social polarization remain missing. The force is capped at PARTIAL until its conceptual scope is better covered. WID data_quality column preserved but NOT used for filtering (official semantics unverified). |
| Internal conflict | scored | 66.0017345 | partial | 2026-Q3 | Initial institutional/conflict-risk proxy: WGI 'Political Stability and Absence of Violence/Terrorism' governance score (2025 revision, 0-100) live 1996-2024 for all 8 countries. It does NOT measure every form of domestic conflict (polarization, protests, distributional tension) — the force is capped at PARTIAL while this proxy is the only input; later ACLED / event data may strengthen it. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. SOURCE indicator, not an Atlas force score. |
| Geography | context_only | — | structural_context_available | 2026-Q3 | Structural context profile `geo_profile_v1` (landlocked status, coastline, island status, land area and maritime access) is available for all tracked countries. It is deliberately static context and has no live time-series input or score. |
| Acts of nature | context_only | — | partial | 2026-Q3 | Verified structural exposure context (Mission 4 §18): WB EN.CLC.MDAT.ZS, an EM-DAT-derived % of population affected by droughts/floods/extreme temperatures averaged over 1990-2009 (published at 2009 only — no annual series). Pandemic and climate-change exposure have no legally accessible provider series ingested yet; missing values mean 'not published', never 'zero events'. |

## Historical raw-indicator changes

The `range baseline` is the first observation in the requested 1980-present window; the `full baseline` is the first observation ever stored. These are deliberately separate views.

| Force / indicator | Earliest | Range baseline | Latest | Range baseline value | Latest value | Range change | Full baseline | Full change | Unit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wealth_opportunity_values_gaps `WEALTH_SHARE_TOP_10` | 1820 | 1980 | 2024 | 0.4081 | 0.6805 | 0.2724 | 1820 | 0.14459999999999995 | share (0-1) |
| resource_allocation_efficiency `GROSS_CAPITAL_FORMATION_GDP` | 1960 | 1980 | 2024 | 34.544058348021 | 40.4815134449629 | 5.937455096941903 | 1960 | 0.9828453121997001 | percent |
| global_openness `EXPORTS_GDP` | 1960 | 1980 | 2025 | 10.1341967491351 | 21.0711983566772 | 10.9370016075421 | 1960 | 17.92470133940984 | percent |
| global_openness `IMPORTS_GDP` | 1960 | 1980 | 2025 | 11.406859455578 | 16.8851895085539 | 5.478330052975901 | 1960 | 13.72611024614299 | percent |
| global_openness `TRADE_BALANCE` | 1960 | 1980 | 2025 | -1.27266270644298 | 4.18600884812329 | 5.45867155456627 | 1960 | 4.198591093266845 | percent |
| trade_capital_flows `EXPORTS_GDP` | 1960 | 1980 | 2025 | 10.1341967491351 | 21.0711983566772 | 10.9370016075421 | 1960 | 17.92470133940984 | percent |
| trade_capital_flows `IMPORTS_GDP` | 1960 | 1980 | 2025 | 11.406859455578 | 16.8851895085539 | 5.478330052975901 | 1960 | 13.72611024614299 | percent |
| trade_capital_flows `TRADE_BALANCE` | 1960 | 1980 | 2025 | -1.27266270644298 | 4.18600884812329 | 5.45867155456627 | 1960 | 4.198591093266845 | percent |
| infrastructure_investment `GROSS_CAPITAL_FORMATION_GDP` | 1960 | 1980 | 2024 | 34.544058348021 | 40.4815134449629 | 5.937455096941903 | 1960 | 0.9828453121997001 | percent |
| resource_allocation_efficiency `GDP_GROWTH` | 1961 | 1980 | 2025 | 7.84141706847441 | 4.95994886240992 | -2.88146820606449 | 1961 | 32.229948866298216 | percent |
| productivity_output_growth `GDP_GROWTH` | 1961 | 1980 | 2025 | 7.84141706847441 | 4.95994886240992 | -2.88146820606449 | 1961 | 32.229948866298216 | percent |
| global_openness `FDI_NET_INFLOWS_GDP` | 1979 | 1980 | 2025 | 0.0297669560676284 | 0.410194399848574 | 0.38042744378094556 | 1979 | 0.41014960047186966 | percent of GDP |
| trade_capital_flows `FDI_NET_INFLOWS_GDP` | 1979 | 1980 | 2025 | 0.0297669560676284 | 0.410194399848574 | 0.38042744378094556 | 1979 | 0.41014960047186966 | percent of GDP |
| cost_competitiveness `REER_INDEX` | 1980 | 1980 | 2025 | 269.954875727707 | 110.093630738086 | -159.861244989621 | 1980 | -159.861244989621 | index |
| wealth_opportunity_values_gaps `GINI_INDEX` | 1981 | 1981 | 2022 | 28.2 | 36.0 | 7.800000000000001 | 1981 | 7.800000000000001 | index (0-100) |
| global_openness `CURRENT_ACCOUNT_GDP` | 1982 | 1982 | 2025 | 2.76132699309013 | 3.76972243689338 | 1.0083954438032499 | 1982 | 1.0083954438032499 | percent |
| trade_capital_flows `CURRENT_ACCOUNT_GDP` | 1982 | 1982 | 2025 | 2.76132699309013 | 3.76972243689338 | 1.0083954438032499 | 1982 | 1.0083954438032499 | percent |
| cost_competitiveness `INFLATION_CPI` | 1987 | 1987 | 2025 | 7.23383553065609 | 0.0595646916565402 | -7.17427083899955 | 1987 | -7.17427083899955 | percent |
| military_strength `MILITARY_EXPENDITURE_USD` | 1989 | 1989 | 2025 | 11251332630.388 | 335524155624.44 | 324272822994.052 | 1989 | 324272822994.052 | current US$ |
| military_strength `MILITARY_EXPENDITURE_GDP` | 1989 | 1989 | 2025 | 2.4471013153 | 1.7247233166 | -0.7223779986999999 | 1989 | -0.7223779986999999 | percent of GDP |
| character_determination `LABOUR_FORCE_PARTICIPATION_RATE` | 1990 | 1990 | 2025 | 79.17 | 64.551 | -14.619 | 1990 | -14.619 | percent |
| indebtedness `CREDIT_TO_GDP_GAP` | 1995 | 1995 | 2026 | -5.7443 | -5.1412 | 0.6030999999999995 | 1995 | 0.6030999999999995 | percentage of GDP |
| indebtedness `GOVERNMENT_DEBT_GDP` | 1995 | 1995 | 2025 | 21.408854 | 98.608625 | 77.199771 | 1995 | 77.199771 | percent |
| leadership_capabilities `GOVERNMENT_EFFECTIVENESS_WGI_SCORE` | 1996 | 1996 | 2025 | 46.5371877 | 65.1127866 | 18.57559890000001 | 1996 | 18.57559890000001 | score 0-100 |
| rule_of_law `RULE_OF_LAW_WGI_SCORE` | 1996 | 1996 | 2025 | 49.5775672 | 51.5591046 | 1.9815374000000006 | 1996 | 1.9815374000000006 | score 0-100 |
| corruption `CONTROL_OF_CORRUPTION_WGI_SCORE` | 1996 | 1996 | 2025 | 41.2298498 | 49.4738147 | 8.243964900000002 | 1996 | 8.243964900000002 | score 0-100 |
| internal_conflict `POLITICAL_STABILITY_WGI_SCORE` | 1996 | 1996 | 2025 | 63.1397287 | 66.0017345 | 2.8620057999999986 | 1996 | 2.8620057999999986 | score 0-100 |
| indebtedness `DEBT_SERVICE_RATIO` | 1999 | 1999 | 2026 | 10.1 | 19.1 | 9.000000000000002 | 1999 | 9.000000000000002 | per cent |
| infrastructure_investment `BROADBAND_PER_100` | 2000 | 2000 | 2024 | 0.00178484057941392 | 47.1933952081567 | 47.19161036757729 | 2000 | 47.19161036757729 | per 100 people |
| acts_of_nature `NATURAL_DISASTER_AFFECTED_PCT` | 2009 | 2009 | 2009 | 7.95097147464036 | 7.95097147464036 | 0.0 | 2009 | 0.0 | percent of population |
| education `TERTIARY_ATTAINMENT_25_34` | 2010 | 2010 | 2010 | 17.948812 | 17.948812 | 0.0 | 2010 | 0.0 | percent |
| resource_allocation_efficiency `LABOUR_PRODUCTIVITY_PER_HOUR` | — | — | — | — | — | — | — | — |  |
| productivity_output_growth `LABOUR_PRODUCTIVITY_PER_HOUR` | — | — | — | — | — | — | — | — |  |
| cost_competitiveness `UNIT_LABOUR_COST_GROWTH` | — | — | — | — | — | — | — | — |  |

## Scientific limitations

- Raw history is latest-vintage evidence; it is not a release-date-safe backtest.
- Missing periods remain missing. No value in this report is interpolated.
- Force statuses distinguish scores, dimension-only signals and context profiles.
- Military expenditure is resources, not total capability.
- Tracked-universe shares are not global shares.
