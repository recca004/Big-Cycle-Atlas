# Germany (DEU) — economic research profile

Generated: 2026-11-25T21:52:40.386227Z
Methodology: experimental, `normalization-v1.4`, `force-aggregation-v1.0`
Requested calculation period: `2026-Q3`
Latest classified composite period: `2025-Q4`
Latest raw observation period: `2026`

## Current interpretation

The production `model_b_domain` result is **58.72213605646205** with stage **DECLINE**, direction `declining`, and coverage ratio `0.6739130434782609`. This is an experimental domestic-condition cycle result, not an international-power ranking and not a claim about an empire life-cycle stage.

## Composite models

| Model | Period | Score | Stage | Coverage |
|---|---:|---:|---|---:|
| `model_a_equal` | 2025-Q4 | 64.72543786271206 | EARLY_DECLINE | 0.6739130434782609 |
| `model_b_domain` | 2025-Q4 | 58.72213605646205 | DECLINE | 0.6739130434782609 |
| `model_c_overlap` | 2025-Q4 | 58.72213605646205 | DECLINE | 0.6739130434782609 |
| `model_d_comparable` | 2025-Q4 | 67.82023338809523 | EARLY_DECLINE | 0.6521739130434783 |

## Seventeen-force evidence

| Force | Status | Level | Coverage | Period | Actual measurement and limitation |
|---|---|---:|---|---|---|
| Leadership capabilities | scored | 82.8363275 | partial | 2026-Q3 | WGI Government Effectiveness (2025 revision, 0-100) is the institutional proxy: quality of public services, civil service, policy formulation and implementation. It measures state capacity, not individual leaders — no subjective leader ratings. Capped PARTIAL: one governance dimension is not the whole leadership-capabilities concept (Sprint 6.21, DEC-041). |
| Education | scored | 40.882102573125 | partial | 2026-Q3 | Live input: OECD tertiary attainment age 25-34 (ISCED 5-8, % of population, annual, Sprint 5.20). Attainment != enrollment. CHN has only 1 data point (2010); IND has 8 sparse data points. Still missing: secondary attainment/enrollment, learning outcomes/test scores, education quality, years of schooling, skills. One tertiary series cannot make Education AVAILABLE — capped at PARTIAL. |
| Character / determination | scored | 46.42857142857143 | partial | 2026-Q3 | PARTIAL proxy (V1 Mission 1, delegated working model): the executable component measures RELATIVE ECONOMIC PARTICIPATION — labour force participation rate (ILO modeled, ages 15+) scored as a WDI-universe percentile. This is a narrow, labeled proxy for economic participation only; it is NOT a measurement of national character or determination. Resourcefulness, entrepreneurship and innovation dimensions remain unmeasured. PARTIAL ceiling enforced; higher participation is not universally positive (documented limitation). |
| Rule of law | scored | 85.067519 | available | 2026-Q3 | World Bank WGI Rule of Law governance score (2025 revision, 0-100 absolute scale) live 1996-present for all 8 countries. Perception-based composite with measurement uncertainty; the 90% CI bounds and source counts are stored in the separate indicator_diagnostics evidence path and never become force inputs. This is a SOURCE indicator for the force, not an Atlas force score. |
| Corruption | scored | 81.8514313 | available | 2026-Q3 | Source is WGI 'Control of Corruption' (2025 revision, 0-100): HIGHER means stronger control of corruption / less corruption — the raw stored value is never reversed or reinterpreted. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. This is a SOURCE indicator, not an Atlas force score. |
| Resource allocation efficiency | context_only | — | partial | 2026-Q3 | Investment & resource-allocation CONTEXT profile (Mission 4 §17): investment effort (GCF % of GDP), output growth, and labour productivity describe the input side — none of them measures allocation efficiency itself, and all three overlap productivity / infrastructure inputs by design (documented, not deduplicated). |
| Global openness | context_only | — | partial | 2026-Q3 | Descriptive openness CONTEXT profile (Mission 4 §16): trade intensity (exports+imports % of GDP, exposed as derived TRADE_OPENNESS_GDP), external balance, current account, FDI inflows, plus population/GDP size context as candidates. Trade intensity is NOT strength (DEC-035) and these inputs overlap trade_capital_flows deliberately. The full force (capital, people, ideas) remains unmeasurable — no level score is claimed. |
| Productivity / output growth | scored | 70.0 | partial | 2026-Q3 | OECD labour productivity per hour (6/8 countries — CHN/IND are not OECD members and cannot receive an OECD-calibrated score). Sprint 6.14 (DEC-042 Option A — owner approved): level = mid-rank percentile within the versioned OECD universe oecd_lpph_v1, period-specific. Capped PARTIAL: OECD relative productivity position only — not the whole productivity/output-growth force, not a global percentile. |
| Cost competitiveness | dimension_only | — | partial | 2026-Q3 | ULC growth is relative-cost meaningful; CPI inflation is a domestic price-pressure input. Relative international competitiveness ultimately needs exchange rates and partner-country price/cost comparisons — CPI alone (e.g. CHN/IND without OECD ULC) makes this force partial, never available. |
| Trade and capital flows | context_only | — | available | 2026-Q3 | World Bank WDI live (2000–2025, all 8 countries): exports/imports of goods and services, the published external balance (direct provider series for trade balance — not derived), and the current account. FDI net inflows (%GDP) live 1990+ all 8 countries (V1 Mission 1). Capital-flow measures beyond the current account and bilateral flows (UN Comtrade) come later. |
| Infrastructure and investment | context_only | — | available | 2026-Q3 | World Bank gross capital formation live (2000–2025, all 8 countries) + fixed broadband per 100 (Mission 2). Investment effort + digital coverage context — NOT infrastructure quality. |
| Indebtedness | scored | 88.9908256880734 | available | 2026-Q3 | Private-sector credit gap + debt service (BIS) + general-government gross debt (IMF WEO, Sprint 5.19). Government debt is a raw level input only — no monotonic 'higher debt = weaker' curve is approved; debt sustainability depends on interest cost, currency, maturity, fiscal capacity, monetary sovereignty, and growth (CONTEXTUAL_DEFERRED in the normalization registry). Sprint 6.13 (DEC-040, ratified) added a score: CONDITION_MINUS_PENALTY composition, level = clamp(DSR + (credit_gap - 50), 0, 100), force-aggregation-v0.4. |
| Military strength | dimension_only | — | partial | 2026-Q3 | Live inputs are spending measures only (World Bank MS.MIL.XPND.CD / MS.MIL.XPND.GD.ZS, underlying source: SIPRI Military Expenditure Database). SIPRI describes military expenditure as an INPUT measure - resources absorbed by the military - not a measure of military capability or security. Personnel capability, equipment quality and quantity, technology, logistics, readiness, combat experience, alliances/force projection, and nuclear capability are not measured, so spending alone can never make this force AVAILABLE (DEC-009 ceiling). |
| Wealth / opportunity / values gaps | scored | 41.48 | partial | 2026-Q3 | Live inputs: World Bank Gini index (income inequality, irregular) + WID top 10% net personal wealth share (wealth concentration, annual, Sprint 5.20). Both are distributional measures — opportunity gaps and values/social polarization remain missing. The force is capped at PARTIAL until its conceptual scope is better covered. WID data_quality column preserved but NOT used for filtering (official semantics unverified). |
| Internal conflict | scored | 69.2575511 | partial | 2026-Q3 | Initial institutional/conflict-risk proxy: WGI 'Political Stability and Absence of Violence/Terrorism' governance score (2025 revision, 0-100) live 1996-2024 for all 8 countries. It does NOT measure every form of domestic conflict (polarization, protests, distributional tension) — the force is capped at PARTIAL while this proxy is the only input; later ACLED / event data may strengthen it. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. SOURCE indicator, not an Atlas force score. |
| Geography | context_only | — | structural_context_available | 2026-Q3 | Structural context profile `geo_profile_v1` (landlocked status, coastline, island status, land area and maritime access) is available for all tracked countries. It is deliberately static context and has no live time-series input or score. |
| Acts of nature | context_only | — | partial | 2026-Q3 | Verified structural exposure context (Mission 4 §18): WB EN.CLC.MDAT.ZS, an EM-DAT-derived % of population affected by droughts/floods/extreme temperatures averaged over 1990-2009 (published at 2009 only — no annual series). Pandemic and climate-change exposure have no legally accessible provider series ingested yet; missing values mean 'not published', never 'zero events'. |

## Historical raw-indicator changes

The `range baseline` is the first observation in the requested 1980-present window; the `full baseline` is the first observation ever stored. These are deliberately separate views.

| Force / indicator | Earliest | Range baseline | Latest | Range baseline value | Latest value | Range change | Full baseline | Full change | Unit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| wealth_opportunity_values_gaps `WEALTH_SHARE_TOP_10` | 1820 | 1980 | 2024 | 0.6226 | 0.5852 | -0.03739999999999999 | 1820 | -0.2873 | share (0-1) |
| cost_competitiveness `INFLATION_CPI` | 1960 | 1980 | 2025 | 5.44105754460346 | 2.17178770949721 | -3.26926983510625 | 1960 | 0.6351753665452 | percent |
| military_strength `MILITARY_EXPENDITURE_USD` | 1960 | 1980 | 2025 | 25009350127.5413 | 113585948604.562 | 88576598477.02069 | 1960 | 110883332123.34631 | current US$ |
| military_strength `MILITARY_EXPENDITURE_GDP` | 1960 | 1980 | 2025 | 2.9476284198 | 2.2685109251 | -0.6791174946999998 | 1960 | -1.483884372 | percent of GDP |
| resource_allocation_efficiency `GDP_GROWTH` | 1961 | 1980 | 2025 | 1.40882864441943 | 0.239578342117881 | -1.169250302301549 | 1961 | -4.058861167640199 | percent |
| productivity_output_growth `GDP_GROWTH` | 1961 | 1980 | 2025 | 1.40882864441943 | 0.239578342117881 | -1.169250302301549 | 1961 | -4.058861167640199 | percent |
| resource_allocation_efficiency `GROSS_CAPITAL_FORMATION_GDP` | 1970 | 1980 | 2025 | 27.6833281172969 | 21.9314930278238 | -5.751835089473097 | 1970 | -11.3470858505442 | percent |
| global_openness `EXPORTS_GDP` | 1970 | 1980 | 2025 | 18.5434109337965 | 40.4347738545071 | 21.8913629207106 | 1970 | 25.3694841450274 | percent |
| global_openness `IMPORTS_GDP` | 1970 | 1980 | 2025 | 23.1529332883341 | 38.0780373654056 | 14.925104077071499 | 1970 | 21.552873922878998 | percent |
| global_openness `TRADE_BALANCE` | 1970 | 1980 | 2025 | -4.60952235453761 | 2.35673648910157 | 6.96625884363918 | 1970 | 3.81661022214851 | percent |
| trade_capital_flows `EXPORTS_GDP` | 1970 | 1980 | 2025 | 18.5434109337965 | 40.4347738545071 | 21.8913629207106 | 1970 | 25.3694841450274 | percent |
| trade_capital_flows `IMPORTS_GDP` | 1970 | 1980 | 2025 | 23.1529332883341 | 38.0780373654056 | 14.925104077071499 | 1970 | 21.552873922878998 | percent |
| trade_capital_flows `TRADE_BALANCE` | 1970 | 1980 | 2025 | -4.60952235453761 | 2.35673648910157 | 6.96625884363918 | 1970 | 3.81661022214851 | percent |
| infrastructure_investment `GROSS_CAPITAL_FORMATION_GDP` | 1970 | 1980 | 2025 | 27.6833281172969 | 21.9314930278238 | -5.751835089473097 | 1970 | -11.3470858505442 | percent |
| indebtedness `CREDIT_TO_GDP_GAP` | 1970 | 1980 | 2026 | -2.6225 | -4.1759 | -1.5534000000000003 | 1970 | -2.1701000000000006 | percentage of GDP |
| global_openness `CURRENT_ACCOUNT_GDP` | 1971 | 1980 | 2025 | -1.64142670824601 | 4.44736378284623 | 6.08879049109224 | 1971 | 4.404884984810335 | percent |
| global_openness `FDI_NET_INFLOWS_GDP` | 1971 | 1980 | 2025 | -0.0195616251555118 | 1.88462297077009 | 1.9041845959256016 | 1971 | 1.4448722291354998 | percent of GDP |
| trade_capital_flows `CURRENT_ACCOUNT_GDP` | 1971 | 1980 | 2025 | -1.64142670824601 | 4.44736378284623 | 6.08879049109224 | 1971 | 4.404884984810335 | percent |
| trade_capital_flows `FDI_NET_INFLOWS_GDP` | 1971 | 1980 | 2025 | -0.0195616251555118 | 1.88462297077009 | 1.9041845959256016 | 1971 | 1.4448722291354998 | percent of GDP |
| cost_competitiveness `REER_INDEX` | 1979 | 1980 | 2025 | 114.652075965685 | 98.8481643556826 | -15.803911610002402 | 1979 | -22.405106901866404 | index |
| education `TERTIARY_ATTAINMENT_25_34` | 1989 | 1989 | 2025 | 18.36923 | 40.882102573125 | 22.512872573125 | 1989 | 22.512872573125 | percent |
| character_determination `LABOUR_FORCE_PARTICIPATION_RATE` | 1990 | 1990 | 2025 | 58.171 | 60.571 | 2.3999999999999986 | 1990 | 2.3999999999999986 | percent |
| resource_allocation_efficiency `LABOUR_PRODUCTIVITY_PER_HOUR` | 1991 | 1991 | 2025 | 57.00911502870846 | 83.2750405959417 | 26.265925567233246 | 1991 | 26.265925567233246 | US dollars per hour, PPP converted |
| productivity_output_growth `LABOUR_PRODUCTIVITY_PER_HOUR` | 1991 | 1991 | 2025 | 57.00911502870846 | 83.2750405959417 | 26.265925567233246 | 1991 | 26.265925567233246 | US dollars per hour, PPP converted |
| indebtedness `GOVERNMENT_DEBT_GDP` | 1991 | 1991 | 2025 | 39.014897 | 62.658294 | 23.643397 | 1991 | 23.643397 | percent |
| wealth_opportunity_values_gaps `GINI_INDEX` | 1991 | 1991 | 2022 | 29.3 | 33.7 | 4.400000000000002 | 1991 | 4.400000000000002 | index (0-100) |
| cost_competitiveness `UNIT_LABOUR_COST_GROWTH` | 1992 | 1992 | 2026 | 7.629594 | 2.702427 | -4.927167 | 1992 | -4.927167 | percent per annum |
| leadership_capabilities `GOVERNMENT_EFFECTIVENESS_WGI_SCORE` | 1996 | 1996 | 2025 | 89.5033062 | 82.8363275 | -6.666978700000001 | 1996 | -6.666978700000001 | score 0-100 |
| rule_of_law `RULE_OF_LAW_WGI_SCORE` | 1996 | 1996 | 2025 | 85.9243886 | 85.067519 | -0.856869599999996 | 1996 | -0.856869599999996 | score 0-100 |
| corruption `CONTROL_OF_CORRUPTION_WGI_SCORE` | 1996 | 1996 | 2025 | 89.1793346 | 81.8514313 | -7.327903300000003 | 1996 | -7.327903300000003 | score 0-100 |
| internal_conflict `POLITICAL_STABILITY_WGI_SCORE` | 1996 | 1996 | 2025 | 88.4494081 | 69.2575511 | -19.191857 | 1996 | -19.191857 | score 0-100 |
| indebtedness `DEBT_SERVICE_RATIO` | 1999 | 1999 | 2026 | 14.0 | 12.2 | -1.8000000000000007 | 1999 | -1.8000000000000007 | per cent |
| infrastructure_investment `BROADBAND_PER_100` | 2000 | 2000 | 2024 | 0.323971739981797 | 45.6069242965787 | 45.282952556596896 | 2000 | 45.282952556596896 | per 100 people |
| acts_of_nature `NATURAL_DISASTER_AFFECTED_PCT` | 2009 | 2009 | 2009 | 0.0328245736854824 | 0.0328245736854824 | 0.0 | 2009 | 0.0 | percent of population |

## Scientific limitations

- Raw history is latest-vintage evidence; it is not a release-date-safe backtest.
- Missing periods remain missing. No value in this report is interpolated.
- Force statuses distinguish scores, dimension-only signals and context profiles.
- Military expenditure is resources, not total capability.
- Tracked-universe shares are not global shares.
