"""Central mapping of canonical Big Cycle Atlas indicators to World Bank series codes.

Every external code here was verified against official World Bank API v2 metadata
(https://api.worldbank.org/v2/indicator/{code}) on 2026-09-08. The adapter and
seed both consume this module — do not scatter WB series codes elsewhere.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class WorldBankMapping:
    indicator_code: str
    external_code: str
    external_name: str
    external_unit: str
    transform_notes: str
    source_key: str = "world_bank"


WORLD_BANK_MAPPINGS: tuple[WorldBankMapping, ...] = (
    WorldBankMapping(
        indicator_code="GDP_GROWTH",
        external_code="NY.GDP.MKTP.KD.ZG",
        external_name="GDP growth (annual %)",
        external_unit="annual %",
        transform_notes="Unit-independent growth rate of constant-price GDP",
    ),
    WorldBankMapping(
        indicator_code="GDP_CURRENT_USD",
        external_code="NY.GDP.MKTP.CD",
        external_name="GDP (current US$)",
        external_unit="current US$",
        transform_notes="Nominal GDP, no inflation adjustment",
    ),
    WorldBankMapping(
        indicator_code="GDP_PER_CAPITA",
        external_code="NY.GDP.PCAP.CD",
        external_name="GDP per capita (current US$)",
        external_unit="current US$ per person",
        transform_notes="Nominal GDP divided by mid-year population",
    ),
    WorldBankMapping(
        indicator_code="EXPORTS_GDP",
        external_code="NE.EXP.GNFS.ZS",
        external_name="Exports of goods and services (% of GDP)",
        external_unit="% of GDP",
        transform_notes="Exports of goods and services as a share of GDP (goods + services scope, matching the canonical indicator)",
    ),
    WorldBankMapping(
        indicator_code="IMPORTS_GDP",
        external_code="NE.IMP.GNFS.ZS",
        external_name="Imports of goods and services (% of GDP)",
        external_unit="% of GDP",
        transform_notes="Imports of goods and services as a share of GDP (goods + services scope, matching the canonical indicator)",
    ),
    WorldBankMapping(
        indicator_code="TRADE_BALANCE",
        external_code="NE.RSB.GNFS.ZS",
        external_name="External balance on goods and services (% of GDP)",
        external_unit="% of GDP",
        transform_notes=(
            "World Bank's published external balance (exports − imports of goods "
            "and services) — used as the direct provider series for Trade Balance, "
            "not derived client-side; scope is consistent with EXPORTS_GDP/IMPORTS_GDP"
        ),
    ),
    WorldBankMapping(
        indicator_code="CURRENT_ACCOUNT_GDP",
        external_code="BN.CAB.XOKA.GD.ZS",
        external_name="Current account balance (% of GDP)",
        external_unit="% of GDP",
        transform_notes="Balance-of-payments current account balance as a share of GDP",
    ),
    WorldBankMapping(
        indicator_code="GROSS_CAPITAL_FORMATION_GDP",
        external_code="NE.GDI.TOTL.ZS",
        external_name="Gross capital formation (% of GDP)",
        external_unit="% of GDP",
        transform_notes="Gross capital formation (fixed assets + inventories) as a share of GDP",
    ),
    WorldBankMapping(
        indicator_code="GINI_INDEX",
        external_code="SI.POV.GINI",
        external_name="Gini index",
        external_unit="index (0-100)",
        transform_notes=(
            "WB Gini index as published (0 = perfect equality, 100 = perfect "
            "inequality; area between the Lorenz curve and the equality line as "
            "a percentage of the maximum). Stored raw — never rescaled, "
            "forward-filled, or derived. Published irregularly: missing years "
            "are gaps, not zeros."
        ),
    ),
    WorldBankMapping(
        indicator_code="INFLATION_CPI",
        external_code="FP.CPI.TOTL.ZG",
        external_name="Inflation, consumer prices (annual %)",
        external_unit="annual %",
        transform_notes=(
            "Annual average consumer price inflation as published. Domestic "
            "price-pressure input - not a relative-competitiveness measure by "
            "itself."
        ),
    ),
    WorldBankMapping(
        indicator_code="MILITARY_EXPENDITURE_USD",
        external_code="MS.MIL.XPND.CD",
        external_name="Military expenditure (current USD)",
        external_unit="current US$",
        transform_notes=(
            "Annual military expenditure in current US dollars, converted at the "
            "exchange rate for the given year. Underlying source: SIPRI Military "
            "Expenditure Database, republished through WDI. Stored raw - an input "
            "proxy for military strength, not a capability measure."
        ),
    ),
    WorldBankMapping(
        indicator_code="MILITARY_EXPENDITURE_GDP",
        external_code="MS.MIL.XPND.GD.ZS",
        external_name="Military expenditure (% of GDP)",
        external_unit="% of GDP",
        transform_notes=(
            "Military expenditure as a share of GDP. Underlying source: SIPRI "
            "Military Expenditure Database, republished through WDI. Stored raw - "
            "an input proxy for military strength, not a capability measure."
        ),
    ),
    WorldBankMapping(
        indicator_code="RULE_OF_LAW_WGI_SCORE",
        external_code="GOV_WGI_RL_SC",
        external_name="Rule of Law - Governance score (0-100)",
        external_unit="score 0-100",
        transform_notes=(
            "WGI 2025-revision absolute governance score (0-100); larger values = "
            "better governance. Perception-based composite with measurement "
            "uncertainty — a source indicator, not an Atlas force score."
        ),
    ),
    WorldBankMapping(
        indicator_code="CONTROL_OF_CORRUPTION_WGI_SCORE",
        external_code="GOV_WGI_CC_SC",
        external_name="Control of Corruption - Governance score (0-100)",
        external_unit="score 0-100",
        transform_notes=(
            "WGI 2025-revision absolute governance score (0-100) for CONTROL of "
            "corruption; larger values = stronger control / less corruption. Stored "
            "raw, never reversed. Perception-based composite with measurement "
            "uncertainty — a source indicator, not an Atlas force score."
        ),
    ),
    WorldBankMapping(
        indicator_code="POLITICAL_STABILITY_WGI_SCORE",
        external_code="GOV_WGI_PV_SC",
        external_name="Political Stability - Governance score (0-100)",
        external_unit="score 0-100",
        transform_notes=(
            "WGI 2025-revision absolute governance score (0-100) for Political "
            "Stability and Absence of Violence/Terrorism; larger values = more "
            "stable. Perception-based composite with measurement uncertainty — a "
            "source indicator, not an Atlas force score."
        ),
    ),
)

_MAPPING_BY_INDICATOR_CODE = {m.indicator_code: m for m in WORLD_BANK_MAPPINGS}
_MAPPING_BY_EXTERNAL_CODE = {m.external_code: m for m in WORLD_BANK_MAPPINGS}


def get_world_bank_mapping(indicator_code: str) -> WorldBankMapping | None:
    return _MAPPING_BY_INDICATOR_CODE.get(indicator_code)


def get_world_bank_mapping_by_external_code(external_code: str) -> WorldBankMapping | None:
    """Reverse lookup: World Bank series code → canonical indicator mapping."""
    return _MAPPING_BY_EXTERNAL_CODE.get(external_code)