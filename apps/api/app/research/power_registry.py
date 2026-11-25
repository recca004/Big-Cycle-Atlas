"""International-power research registry.

These definitions describe measurable evidence only. They do not define a
composite international-power score or ranking.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PowerMeasureDefinition:
    dimension: str
    measurement: str
    indicator_code: str | None
    external_code: str | None
    source_key: str
    unit: str
    frequency: str
    entity_type: str  # tracked_country | currency_area | global_denominator
    reference_population: str
    comparison_semantics: str
    global_denominator_code: str | None = None
    limitations: str = ""


POWER_MEASURE_DEFINITIONS: tuple[PowerMeasureDefinition, ...] = (
    PowerMeasureDefinition(
        "economic_output", "Nominal GDP", "GDP_CURRENT_USD",
        "NY.GDP.MKTP.CD", "world_bank", "current US$", "annual",
        "tracked_country", "world", "global_share_of_nominal_gdp",
        "NY.GDP.MKTP.CD", "Market-exchange-rate GDP; not welfare or per-capita capability.",
    ),
    PowerMeasureDefinition(
        "economic_output", "PPP GDP", "GDP_PPP_CURRENT_INTL",
        "NY.GDP.MKTP.PP.CD", "world_bank", "current international $", "annual",
        "tracked_country", "world", "global_share_of_ppp_gdp",
        "NY.GDP.MKTP.PP.CD", "PPP conversions are method-specific; do not mix base years.",
    ),
    PowerMeasureDefinition(
        "economic_output", "Real GDP (constant 2015 US$)", "GDP_REAL_CONSTANT_USD",
        "NY.GDP.MKTP.KD", "world_bank", "constant 2015 US$", "annual",
        "tracked_country", "world", "global_share_of_real_output",
        "NY.GDP.MKTP.KD", "Constant-price volume; provider base year fixed.",
    ),
    PowerMeasureDefinition(
        "economic_output", "Nominal GDP per capita", "GDP_PER_CAPITA",
        "NY.GDP.PCAP.CD", "world_bank", "current US$ per person", "annual",
        "tracked_country", "tracked_8", "level_comparison",
        None, "Average income, not total economic scale.",
    ),
    PowerMeasureDefinition(
        "international_trade", "Merchandise exports", "MERCHANDISE_EXPORTS_USD",
        "TX.VAL.MRCH.CD.WT", "world_bank", "current US$", "annual",
        "tracked_country", "world", "global_share_of_merchandise_exports",
        "TX.VAL.MRCH.CD.WT", "Goods only; excludes services.",
    ),
    PowerMeasureDefinition(
        "international_trade", "Merchandise imports", "MERCHANDISE_IMPORTS_USD",
        "TM.VAL.MRCH.CD.WT", "world_bank", "current US$", "annual",
        "tracked_country", "world", "global_share_of_merchandise_imports",
        "TM.VAL.MRCH.CD.WT", "Goods only; excludes services.",
    ),
    PowerMeasureDefinition(
        "international_trade", "Commercial service exports", "COMMERCIAL_SERVICE_EXPORTS_USD",
        "TX.VAL.SERV.CD.WT", "world_bank", "current US$", "annual",
        "tracked_country", "world", "global_share_of_commercial_service_exports",
        "TX.VAL.SERV.CD.WT", "Services only; separate from merchandise trade.",
    ),
    PowerMeasureDefinition(
        "international_trade", "Commercial service imports", "COMMERCIAL_SERVICE_IMPORTS_USD",
        "TM.VAL.SERV.CD.WT", "world_bank", "current US$", "annual",
        "tracked_country", "world", "global_share_of_commercial_service_imports",
        "TM.VAL.SERV.CD.WT", "Services only; separate from merchandise trade.",
    ),
    PowerMeasureDefinition(
        "international_trade", "Trade intensity", "EXPORTS_GDP",
        "NE.EXP.GNFS.ZS", "world_bank", "% of GDP", "annual",
        "tracked_country", "none", "openness_not_market_share",
        None, "Exports/GDP is openness, never global market share.",
    ),
    PowerMeasureDefinition(
        "military_strength", "Military expenditure", "MILITARY_EXPENDITURE_USD",
        "MS.MIL.XPND.CD", "world_bank", "current US$", "annual",
        "tracked_country", "world", "global_share_of_military_expenditure",
        "MS.MIL.XPND.CD", "SIPRI input measure republished by WDI; resources, not capability.",
    ),
    PowerMeasureDefinition(
        "military_strength", "Military expenditure share of GDP", "MILITARY_EXPENDITURE_GDP",
        "MS.MIL.XPND.GD.ZS", "world_bank", "% of GDP", "annual",
        "tracked_country", "none", "burden_share",
        None, "Defence burden; not total capability.",
    ),
    PowerMeasureDefinition(
        "innovation_technology", "R&D expenditure", "RND_EXPENDITURE_GDP",
        "GB.XPD.RSDV.GD.ZS", "world_bank", "% of GDP", "annual",
        "tracked_country", "none", "innovation_input_intensity",
        None, "Input intensity, not innovation output or leadership.",
    ),
    PowerMeasureDefinition(
        "innovation_technology", "Resident patent applications", "PATENT_APPLICATIONS_RESIDENT",
        "IP.PAT.RESD", "world_bank", "applications", "annual",
        "tracked_country", "world", "innovation_output_count",
        "IP.PAT.RESD", "Counts do not measure patent quality or value.",
    ),
    PowerMeasureDefinition(
        "innovation_technology", "Non-resident patent applications", "PATENT_APPLICATIONS_NONRESIDENT",
        "IP.PAT.NRES", "world_bank", "applications", "annual",
        "tracked_country", "world", "foreign_innovation_interest_count",
        "IP.PAT.NRES", "Filing-count proxy; not technological leadership.",
    ),
    PowerMeasureDefinition(
        "innovation_technology", "Researchers in R&D", "RESEARCHERS_PER_MILLION",
        "SP.POP.SCIE.RD.P6", "world_bank", "per million people", "annual",
        "tracked_country", "none", "research_capacity_density",
        None, "Density measure; not total research output or quality.",
    ),
    PowerMeasureDefinition(
        "innovation_technology", "High-technology exports", "HIGH_TECHNOLOGY_EXPORTS_USD",
        "TX.VAL.TECH.CD", "world_bank", "current US$", "annual",
        "tracked_country", "world", "global_share_of_high_technology_exports",
        "TX.VAL.TECH.CD", "Trade-output proxy; classification and assembly effects apply.",
    ),
    PowerMeasureDefinition(
        "cost_competitiveness", "Real effective exchange rate", "REER_INDEX",
        "PX.REX.REER", "world_bank", "index", "annual",
        "tracked_country", "none", "relative_price_index",
        None, "Rising REER means real appreciation, not automatically weakness.",
    ),
    PowerMeasureDefinition(
        "education", "Tertiary attainment age 25-34", "TERTIARY_ATTAINMENT_25_34",
        "OECD EAG LSO NEAC", "oecd", "% of population", "annual",
        "tracked_country", "oecd_reporting", "education_attainment",
        None, "Sparse CHN/IND coverage; attainment is not learning quality.",
    ),
    PowerMeasureDefinition(
        "financial_centre_strength", "Listed market capitalisation", "STOCK_MARKET_CAP_GDP",
        "CM.MKT.LCAP.GD.ZS", "world_bank", "% of GDP", "annual",
        "tracked_country", "none", "capital_market_depth",
        None, "Domestic listed-market depth; not an international-centre score.",
    ),
    PowerMeasureDefinition(
        "financial_centre_strength", "Domestic credit to private sector", "DOMESTIC_CREDIT_PRIVATE_GDP",
        "FS.AST.PRVT.GD.ZS", "world_bank", "% of GDP", "annual",
        "tracked_country", "none", "financial_depth",
        None, "Credit depth is not the same as international intermediation.",
    ),
    PowerMeasureDefinition(
        "financial_centre_strength", "Broad money", "BROAD_MONEY_GDP",
        "FM.LBL.BMNY.GD.ZS", "world_bank", "% of GDP", "annual",
        "tracked_country", "none", "monetary_system_depth",
        None, "System depth; not reserve status or global financial influence.",
    ),
    PowerMeasureDefinition(
        "reserve_currency_status", "Official reserve share", None,
        None, "imf_cofer", "% of allocated reserves", "quarterly",
        "currency_area", "world_allocated_reserves", "currency_level_share",
        None, "Not yet ingested; unreported currencies remain unavailable, never zero.",
    ),
    PowerMeasureDefinition(
        "reserve_currency_status", "Foreign-exchange turnover share", None,
        None, "bis_triennial", "% of turnover", "triennial",
        "currency_area", "global_fx_turnover", "currency_level_share",
        None, "Not yet ingested; currency-level evidence, not country score.",
    ),
)

POWER_MEASURES_BY_INDICATOR = {
    m.indicator_code: m for m in POWER_MEASURE_DEFINITIONS if m.indicator_code
}

GLOBAL_DENOMINATOR_SERIES: dict[str, dict[str, str]] = {
    m.global_denominator_code: {
        "universe_code": "world_wdi_denominator_v1",
        "indicator_code": m.indicator_code or m.measurement,
        "entity": "WLD",
        "entity_name": "World",
    }
    for m in POWER_MEASURE_DEFINITIONS
    if m.global_denominator_code
}

CURRENCY_RESEARCH_ENTITIES: dict[str, dict[str, str]] = {
    "USD": {"entity": "USD", "scope": "currency", "issuer_area": "United States", "country_iso3": "USA"},
    "EUR": {"entity": "EUR", "scope": "currency_area", "issuer_area": "Euro area", "country_iso3": ""},
    "CNY": {"entity": "CNY", "scope": "currency", "issuer_area": "China", "country_iso3": "CHN"},
    "JPY": {"entity": "JPY", "scope": "currency", "issuer_area": "Japan", "country_iso3": "JPN"},
    "GBP": {"entity": "GBP", "scope": "currency", "issuer_area": "United Kingdom", "country_iso3": "GBR"},
    "CHF": {"entity": "CHF", "scope": "currency", "issuer_area": "Switzerland", "country_iso3": "CHE"},
    "INR": {"entity": "INR", "scope": "currency", "issuer_area": "India", "country_iso3": "IND"},
    "DEM": {"entity": "DEM", "scope": "historical_currency", "issuer_area": "Germany", "country_iso3": "DEU"},
    "FRF": {"entity": "FRF", "scope": "historical_currency", "issuer_area": "France", "country_iso3": "FRA"},
}

HISTORICAL_BOUNDARIES: tuple[dict[str, str], ...] = (
    {
        "country": "DEU",
        "statistical_entity": "Germany (current boundaries)",
        "applies_from": "1991-01-01",
        "applies_to": "present",
        "interpretation": "Post-reunification Germany; directly comparable to current DEU identity.",
        "source_methodology": "Atlas boundary registry v1; provider-specific definitions still apply.",
    },
    {
        "country": "DEU",
        "statistical_entity": "Federal Republic of Germany / provider Germany series",
        "applies_from": "series_start",
        "applies_to": "1990-12-31",
        "interpretation": (
            "Pre-1991 observations must be treated as provider-labelled Germany/Federal "
            "Republic history, not silently joined to a combined East+West territory."
        ),
        "source_methodology": "World Bank/OECD/IMF provider conventions; unresolved territorial scope flagged.",
    },
    {
        "country": "CHN",
        "statistical_entity": "China, mainland statistical coverage",
        "applies_from": "series_start",
        "applies_to": "present",
        "interpretation": "Provider definitions may exclude Hong Kong, Macao and Taiwan unless explicitly stated.",
        "source_methodology": "Atlas boundary registry v1; provider notes govern each series.",
    },
)


def power_measure_by_indicator(indicator_code: str) -> PowerMeasureDefinition | None:
    return POWER_MEASURES_BY_INDICATOR.get(indicator_code)
