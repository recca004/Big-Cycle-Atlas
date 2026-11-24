# Force completion matrix (2026-03, normalization-v1.0 / force-aggregation-v0.6)

Implementation types: **A** approved numerical · **B** partial numerical (PARTIAL ceiling) · **C** dimension-only · **D** context-only research module.

| # | Force | Type | Level | Data | Blocker |
|---|-------|------|-------|------|---------|
| 1 | education | B | TERTIARY_ATTAINMENT_25_34 direct_0_100 | OECD, 6/8 | — |
| 2 | character_determination | D | none | LFP/R&D candidates imported | no defensible proxy for "character"; context module pending |
| 3 | rule_of_law | A | WGI RL direct_0_100 (+rel+momentum) | WGI, 8/8 | — |
| 4 | corruption | A | WGI CC direct_0_100 (+rel+momentum) | WGI, 8/8 | — |
| 5 | resource_allocation_efficiency | D | none | GCF context | definition + overlap map needed |
| 6 | global_openness | D | none | trade %GDP + population | DEC-035: intensity ≠ strength; structural model research |
| 7 | productivity_output_growth | B | LPPH OECD reference percentile | OECD, 6/8 | CHN/IND non-OECD; momentum (Option C) approved — implementing |
| 8 | cost_competitiveness | D | none | ULC context | REER import + method (DEC-018 open) |
| 9 | trade_capital_flows | D | none | exports/imports/CA %GDP | DEC-039 DEFER: no parameter-free composition; dimensions research |
| 10 | indebtedness | A | DSR own-history + credit-gap penalty | BIS+IMF, 8/8 | — (DEC-040 ratified) |
| 11 | wealth_opportunity_values_gaps | B | WID top-10 complement_0_100 | WID+WB, 8/8 | — |
| 12 | internal_conflict | B | WGI PS direct_0_100 | WGI, 8/8 | direct event data (future) |
| 13 | infrastructure_investment | D | none | GCF context | DEC-036 DEFER: LPI discontinued, saturation; new sources needed |
| 14 | leadership_capabilities | B | WGI GE direct_0_100 | WGI, 8/8 | — (DEC-041 ratified; overlap review pending composite) |
| 15 | military_strength | D | none | SIPRI/WB exp. USD + %GDP (1,372 obs) | level method — delegated proxy under evaluation |
| 16 | acts_of_nature | D | none | none | EM-DAT/UNDRR research + licensing |
| 17 | geography | D | none | none | structural (static) profile — versioned, no fake history |

Legend: 8/17 numerical (1 A-partial… see ceiling column in force_definitions.py); every D-type keeps real context data where imported, never fabricated scores.
