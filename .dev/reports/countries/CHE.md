# Switzerland (CHE) — economic research profile

Generated: 2026-11-26T09:05:19.352324Z
Methodology: experimental, `normalization-v1.4`, `force-aggregation-v1.0`
Requested calculation period: `2026-Q3`
Latest classified composite period: `2025-Q4`
Latest raw observation period: `2026`

## Current interpretation

The production `model_b_domain` result is **68.0789438187591** with stage **EARLY_DECLINE**, direction `declining`, and coverage ratio `0.6739130434782609`. This is an experimental domestic-condition cycle result, not an international-power ranking and not a claim about an empire life-cycle stage.

## Composite models

| Model | Period | Score | Stage | Coverage |
|---|---:|---:|---|---:|
| `model_a_equal` | 2025-Q4 | 74.96522753304481 | EARLY_DECLINE | 0.6739130434782609 |
| `model_b_domain` | 2025-Q4 | 68.0789438187591 | EARLY_DECLINE | 0.6739130434782609 |
| `model_c_overlap` | 2025-Q4 | 68.0789438187591 | EARLY_DECLINE | 0.6739130434782609 |
| `model_d_comparable` | 2025-Q4 | 77.47208624175823 | EARLY_DECLINE | 0.6521739130434783 |

## Seventeen-force evidence

| Force | Status | Level | Coverage | Period | Actual measurement and limitation |
|---|---|---:|---|---|---|
| Leadership capabilities | scored | 92.6372053 | partial | 2026-Q3 | WGI Government Effectiveness (2025 revision, 0-100) is the institutional proxy: quality of public services, civil service, policy formulation and implementation. It measures state capacity, not individual leaders — no subjective leader ratings. Capped PARTIAL: one governance dimension is not the whole leadership-capabilities concept (Sprint 6.21, DEC-041). |
| Education | scored | 50.6035885280948 | partial | 2026-Q3 | Live input: OECD tertiary attainment age 25-34 (ISCED 5-8, % of population, annual, Sprint 5.20). Attainment != enrollment. CHN has only 1 data point (2010); IND has 8 sparse data points. Still missing: secondary attainment/enrollment, learning outcomes/test scores, education quality, years of schooling, skills. One tertiary series cannot make Education AVAILABLE — capped at PARTIAL. |
| Character / determination | scored | 74.45054945054945 | partial | 2026-Q3 | PARTIAL proxy (V1 Mission 1, delegated working model): the executable component measures RELATIVE ECONOMIC PARTICIPATION — labour force participation rate (ILO modeled, ages 15+) scored as a WDI-universe percentile. This is a narrow, labeled proxy for economic participation only; it is NOT a measurement of national character or determination. Resourcefulness, entrepreneurship and innovation dimensions remain unmeasured. PARTIAL ceiling enforced; higher participation is not universally positive (documented limitation). |
| Rule of law | scored | 87.2654703 | available | 2026-Q3 | World Bank WGI Rule of Law governance score (2025 revision, 0-100 absolute scale) live 1996-present for all 8 countries. Perception-based composite with measurement uncertainty; the 90% CI bounds and source counts are stored in the separate indicator_diagnostics evidence path and never become force inputs. This is a SOURCE indicator for the force, not an Atlas force score. |
| Corruption | scored | 88.0512603 | available | 2026-Q3 | Source is WGI 'Control of Corruption' (2025 revision, 0-100): HIGHER means stronger control of corruption / less corruption — the raw stored value is never reversed or reinterpreted. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. This is a SOURCE indicator, not an Atlas force score. |
| Resource allocation efficiency | context_only | — | partial | 2026-Q3 | Investment & resource-allocation CONTEXT profile (Mission 4 §17): investment effort (GCF % of GDP), output growth, and labour productivity describe the input side — none of them measures allocation efficiency itself, and all three overlap productivity / infrastructure inputs by design (documented, not deduplicated). |
| Global openness | context_only | — | partial | 2026-Q3 | Descriptive openness CONTEXT profile (Mission 4 §16): trade intensity (exports+imports % of GDP, exposed as derived TRADE_OPENNESS_GDP), external balance, current account, FDI inflows, plus population/GDP size context as candidates. Trade intensity is NOT strength (DEC-035) and these inputs overlap trade_capital_flows deliberately. The full force (capital, people, ideas) remains unmeasurable — no level score is claimed. |
| Productivity / output growth | scored | 84.28571428571429 | partial | 2026-Q3 | OECD labour productivity per hour (6/8 countries — CHN/IND are not OECD members and cannot receive an OECD-calibrated score). Sprint 6.14 (DEC-042 Option A — owner approved): level = mid-rank percentile within the versioned OECD universe oecd_lpph_v1, period-specific. Capped PARTIAL: OECD relative productivity position only — not the whole productivity/output-growth force, not a global percentile. |
| Cost competitiveness | dimension_only | — | partial | 2026-Q3 | ULC growth is relative-cost meaningful; CPI inflation is a domestic price-pressure input. Relative international competitiveness ultimately needs exchange rates and partner-country price/cost comparisons — CPI alone (e.g. CHN/IND without OECD ULC) makes this force partial, never available. |
| Trade and capital flows | context_only | — | available | 2026-Q3 | World Bank WDI live (2000–2025, all 8 countries): exports/imports of goods and services, the published external balance (direct provider series for trade balance — not derived), and the current account. FDI net inflows (%GDP) live 1990+ all 8 countries (V1 Mission 1). Capital-flow measures beyond the current account and bilateral flows (UN Comtrade) come later. |
| Infrastructure and investment | context_only | — | available | 2026-Q3 | World Bank gross capital formation live (2000–2025, all 8 countries) + fixed broadband per 100 (Mission 2). Investment effort + digital coverage context — NOT infrastructure quality. |
| Indebtedness | scored | 7.339449541284409 | available | 2026-Q3 | Private-sector credit gap + debt service (BIS) + general-government gross debt (IMF WEO, Sprint 5.19). Government debt is a raw level input only — no monotonic 'higher debt = weaker' curve is approved; debt sustainability depends on interest cost, currency, maturity, fiscal capacity, monetary sovereignty, and growth (CONTEXTUAL_DEFERRED in the normalization registry). Sprint 6.13 (DEC-040, ratified) added a score: CONDITION_MINUS_PENALTY composition, level = clamp(DSR + (credit_gap - 50), 0, 100), force-aggregation-v0.4. |
| Military strength | dimension_only | — | partial | 2026-Q3 | Live inputs are spending measures only (World Bank MS.MIL.XPND.CD / MS.MIL.XPND.GD.ZS, underlying source: SIPRI Military Expenditure Database). SIPRI describes military expenditure as an INPUT measure - resources absorbed by the military - not a measure of military capability or security. Personnel capability, equipment quality and quantity, technology, logistics, readiness, combat experience, alliances/force projection, and nuclear capability are not measured, so spending alone can never make this force AVAILABLE (DEC-009 ceiling). |
| Wealth / opportunity / values gaps | scored | 37.21 | partial | 2026-Q3 | Live inputs: World Bank Gini index (income inequality, irregular) + WID top 10% net personal wealth share (wealth concentration, annual, Sprint 5.20). Both are distributional measures — opportunity gaps and values/social polarization remain missing. The force is capped at PARTIAL until its conceptual scope is better covered. WID data_quality column preserved but NOT used for filtering (official semantics unverified). |
| Internal conflict | scored | 85.2180321 | partial | 2026-Q3 | Initial institutional/conflict-risk proxy: WGI 'Political Stability and Absence of Violence/Terrorism' governance score (2025 revision, 0-100) live 1996-2024 for all 8 countries. It does NOT measure every form of domestic conflict (polarization, protests, distributional tension) — the force is capped at PARTIAL while this proxy is the only input; later ACLED / event data may strengthen it. Perception-based composite; uncertainty bounds/source counts are stored separately as indicator diagnostics. SOURCE indicator, not an Atlas force score. |
| Geography | context_only | — | structural_context_available | 2026-Q3 | Structural context profile `geo_profile_v1` (landlocked status, coastline, island status, land area and maritime access) is available for all tracked countries. It is deliberately static context and has no live time-series input or score. |
| Acts of nature | context_only | — | partial | 2026-Q3 | Verified structural exposure context (Mission 4 §18): WB EN.CLC.MDAT.ZS, an EM-DAT-derived % of population affected by droughts/floods/extreme temperatures averaged over 1990-2009 (published at 2009 only — no annual series). Pandemic and climate-change exposure have no legally accessible provider series ingested yet; missing values mean 'not published', never 'zero events'. |

## Historical raw-indicator changes

The `range baseline` is the first observation in the requested 1980-present window; the `full baseline` is the first observation ever stored. These are deliberately separate views.

| Force / indicator | Earliest | Range baseline | Latest | Range baseline value | Latest value | Range change | Full baseline | Full change | Unit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| cost_competitiveness `INFLATION_CPI` | 1960 | 1980 | 2025 | 4.0225008483901 | 0.154376978290185 | -3.8681238700999154 | 1960 | -1.2844177249206852 | percent |
| military_strength `MILITARY_EXPENDITURE_USD` | 1960 | 1980 | 2025 | 1996765550.12502 | 7591405901.06939 | 5594640350.94437 | 1960 | 7391312142.851254 | current US$ |
| military_strength `MILITARY_EXPENDITURE_GDP` | 1960 | 1980 | 2025 | 1.6786065459 | 0.7569245383 | -0.9216820076 | 1960 | -1.5845258230000003 | percent of GDP |
| resource_allocation_efficiency `GDP_GROWTH` | 1961 | 1980 | 2025 | 1.69997141281395 | 1.30007790958307 | -0.39989350323088013 | 1961 | -4.38121484542819 | percent |
| productivity_output_growth `GDP_GROWTH` | 1961 | 1980 | 2025 | 1.69997141281395 | 1.30007790958307 | -0.39989350323088013 | 1961 | -4.38121484542819 | percent |
| resource_allocation_efficiency `GROSS_CAPITAL_FORMATION_GDP` | 1970 | 1980 | 2025 | 37.4383034941476 | 29.4875351254104 | -7.950768368737197 | 1970 | -14.9193909721448 | percent |
| global_openness `EXPORTS_GDP` | 1970 | 1980 | 2025 | 45.371812500301 | 78.0527434720482 | 32.68093097174721 | 1970 | 37.58539910379331 | percent |
| global_openness `IMPORTS_GDP` | 1970 | 1980 | 2025 | 48.1690966883791 | 69.109307845911 | 20.940211157531905 | 1970 | 27.879700366317508 | percent |
| global_openness `TRADE_BALANCE` | 1970 | 1980 | 2025 | -2.7972841880781 | 8.94343562613719 | 11.74071981421529 | 1970 | 9.705698737475721 | percent |
| trade_capital_flows `EXPORTS_GDP` | 1970 | 1980 | 2025 | 45.371812500301 | 78.0527434720482 | 32.68093097174721 | 1970 | 37.58539910379331 | percent |
| trade_capital_flows `IMPORTS_GDP` | 1970 | 1980 | 2025 | 48.1690966883791 | 69.109307845911 | 20.940211157531905 | 1970 | 27.879700366317508 | percent |
| trade_capital_flows `TRADE_BALANCE` | 1970 | 1980 | 2025 | -2.7972841880781 | 8.94343562613719 | 11.74071981421529 | 1970 | 9.705698737475721 | percent |
| infrastructure_investment `GROSS_CAPITAL_FORMATION_GDP` | 1970 | 1980 | 2025 | 37.4383034941476 | 29.4875351254104 | -7.950768368737197 | 1970 | -14.9193909721448 | percent |
| indebtedness `CREDIT_TO_GDP_GAP` | 1970 | 1980 | 2026 | 11.4545 | -11.8457 | -23.3002 | 1970 | -14.045300000000001 | percentage of GDP |
| global_openness `CURRENT_ACCOUNT_GDP` | 1977 | 1980 | 2025 | -0.161657174905759 | 6.24639351116552 | 6.408050686071279 | 1977 | 3.65493668424784 | percent |
| trade_capital_flows `CURRENT_ACCOUNT_GDP` | 1977 | 1980 | 2025 | -0.161657174905759 | 6.24639351116552 | 6.408050686071279 | 1977 | 3.65493668424784 | percent |
| cost_competitiveness `REER_INDEX` | 1979 | 1980 | 2025 | 85.7112774934733 | 112.267720977404 | 26.556443483930693 | 1979 | 19.176488130146694 | index |
| wealth_opportunity_values_gaps `WEALTH_SHARE_TOP_10` | 1980 | 1980 | 2024 | 0.5463 | 0.6279 | 0.0816 | 1980 | 0.0816 | share (0-1) |
| wealth_opportunity_values_gaps `GINI_INDEX` | 1982 | 1982 | 2023 | 36.0 | 33.5 | -2.5 | 1982 | -2.5 | index (0-100) |
| global_openness `FDI_NET_INFLOWS_GDP` | 1983 | 1983 | 2025 | 0.55228091479742 | 0.00152330843935289 | -0.5507576063580671 | 1983 | -0.5507576063580671 | percent of GDP |
| trade_capital_flows `FDI_NET_INFLOWS_GDP` | 1983 | 1983 | 2025 | 0.55228091479742 | 0.00152330843935289 | -0.5507576063580671 | 1983 | -0.5507576063580671 | percent of GDP |
| education `TERTIARY_ATTAINMENT_25_34` | 1989 | 1989 | 2025 | 27.683844 | 50.6035885280948 | 22.919744528094796 | 1989 | 22.919744528094796 | percent |
| character_determination `LABOUR_FORCE_PARTICIPATION_RATE` | 1990 | 1990 | 2025 | 64.659 | 66.747 | 2.087999999999994 | 1990 | 2.087999999999994 | percent |
| indebtedness `GOVERNMENT_DEBT_GDP` | 1990 | 1990 | 2025 | 33.065303 | 40.058304 | 6.993001 | 1990 | 6.993001 | percent |
| resource_allocation_efficiency `LABOUR_PRODUCTIVITY_PER_HOUR` | 1991 | 1991 | 2025 | 59.37494007698761 | 90.51776442200304 | 31.142824345015427 | 1991 | 31.142824345015427 | US dollars per hour, PPP converted |
| productivity_output_growth `LABOUR_PRODUCTIVITY_PER_HOUR` | 1991 | 1991 | 2025 | 59.37494007698761 | 90.51776442200304 | 31.142824345015427 | 1991 | 31.142824345015427 | US dollars per hour, PPP converted |
| leadership_capabilities `GOVERNMENT_EFFECTIVENESS_WGI_SCORE` | 1996 | 1996 | 2025 | 90.5427164 | 92.6372053 | 2.0944889000000018 | 1996 | 2.0944889000000018 | score 0-100 |
| rule_of_law `RULE_OF_LAW_WGI_SCORE` | 1996 | 1996 | 2025 | 90.713279 | 87.2654703 | -3.447808699999996 | 1996 | -3.447808699999996 | score 0-100 |
| corruption `CONTROL_OF_CORRUPTION_WGI_SCORE` | 1996 | 1996 | 2025 | 90.553786 | 88.0512603 | -2.5025257000000067 | 1996 | -2.5025257000000067 | score 0-100 |
| cost_competitiveness `UNIT_LABOUR_COST_GROWTH` | 1996 | 1996 | 2026 | 0.3370476 | -0.808922 | -1.1459696 | 1996 | -1.1459696 | percent per annum |
| internal_conflict `POLITICAL_STABILITY_WGI_SCORE` | 1996 | 1996 | 2025 | 92.3756057 | 85.2180321 | -7.157573599999992 | 1996 | -7.157573599999992 | score 0-100 |
| indebtedness `DEBT_SERVICE_RATIO` | 1999 | 1999 | 2026 | 17.0 | 20.0 | 3.0 | 1999 | 3.0 | per cent |
| infrastructure_investment `BROADBAND_PER_100` | 2000 | 2000 | 2024 | 0.785299902965017 | 47.0197818175134 | 46.23448191454838 | 2000 | 46.23448191454838 | per 100 people |
| acts_of_nature `NATURAL_DISASTER_AFFECTED_PCT` | 2009 | 2009 | 2009 | 0.00388788412428912 | 0.00388788412428912 | 0.0 | 2009 | 0.0 | percent of population |

## Scientific limitations

- Raw history is latest-vintage evidence; it is not a release-date-safe backtest.
- Missing periods remain missing. No value in this report is interpolated.
- Force statuses distinguish scores, dimension-only signals and context profiles.
- Military expenditure is resources, not total capability.
- Tracked-universe shares are not global shares.
