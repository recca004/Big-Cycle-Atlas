# Force completion matrix (2026-11-25, normalization-v1.3 / force-aggregation-v1.0)

Primary classes are mutually exclusive and sum to 17: level_published 9 · dimension_only 2 · context_profile 3 · deferred 3 (see /api/research/progress).

Implementation types: **A** approved numerical · **B** partial numerical (PARTIAL ceiling) · **C** dimension-only · **D** context-only research module.

| # | Force | Type | Level | Data | Blocker |
|---|-------|------|-------|------|---------|
| 1 | education | B | TERTIARY_ATTAINMENT_25_34 direct_0_100 | OECD, 6/8 | — |
| 2 | character_determination | B | LFP WDI-universe percentile (+pct momentum) | WB SL.TLF.CACT.ZS + wdi_lfp_v1 universe, 8/8 | narrow participation proxy only — never "character"; entrepreneurship/innovation unmeasured |
| 3 | rule_of_law | A | WGI RL direct_0_100 (+rel+momentum) | WGI, 8/8 | — |
| 4 | corruption | A | WGI CC direct_0_100 (+rel+momentum) | WGI, 8/8 | — |
| 5 | resource_allocation_efficiency | D | none | GCF context | definition + overlap map needed |
| 6 | global_openness | D | none | trade %GDP + population | DEC-035: intensity ≠ strength; structural model research |
| 7 | productivity_output_growth | B | LPPH OECD percentile + own-history % momentum (3/5/10y) | OECD, 6/8 | CHN/IND non-OECD (no compatible source verified) |
| 8 | cost_competitiveness | dimension_only | REER momentum live (+10.96% 5y) | ULC/CPI context | level method open (DEC-018) |
| 9 | trade_capital_flows | D | none | exports/imports/CA/FDI %GDP (all live, 8/8) | DEC-039 DEFER: context module with 5 real series |
| 10 | indebtedness | A | DSR own-history + credit-gap penalty | BIS+IMF, 8/8 | — (DEC-040 ratified) |
| 11 | wealth_opportunity_values_gaps | B | WID top-10 complement_0_100 | WID+WB, 8/8 | — |
| 12 | internal_conflict | B | WGI PS direct_0_100 | WGI, 8/8 | direct event data (future) |
| 13 | infrastructure_investment | D | none | GCF context | DEC-036 DEFER: LPI discontinued, saturation; new sources needed |
| 14 | leadership_capabilities | B | WGI GE direct_0_100 | WGI, 8/8 | — (DEC-041 ratified; overlap review pending composite) |
| 15 | military_strength | C | level deferred; relative = share of tracked-8 defence spending | SIPRI/WB 1,372 obs | relative_share = input measure, never capability |
| 16 | acts_of_nature | D | none | none | EM-DAT/UNDRR research + licensing |
| 17 | geography | context_profile | structural profile live via /api/research/countries/{iso3}/geography | — | static facts only, no score |

Legend: 9/17 scored (8 approved/partial + 1 type-B proxy), 1 type-C dimension, 7 context modules (1 A-partial… see ceiling column in force_definitions.py); every D-type keeps real context data where imported, never fabricated scores.
