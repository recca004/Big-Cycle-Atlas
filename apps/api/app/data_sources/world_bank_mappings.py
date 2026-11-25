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
        indicator_code="POPULATION",
        external_code="SP.POP.TOTL",
        external_name="Population, total",
        external_unit="count (persons)",
        transform_notes=(
            "Total mid-year population (de facto). Normalization denominator / "
            "context input — never rescaled."
        ),
    ),
    WorldBankMapping(
        indicator_code="RND_EXPENDITURE_GDP",
        external_code="GB.XPD.RSDV.GD.ZS",
        external_name="Research and development expenditure (% of GDP)",
        external_unit="% of GDP",
        transform_notes=(
            "Gross domestic expenditure on R&D as % of GDP (UNESCO UIS "
            "underlying). Published with multi-year lag; missing years are "
            "gaps, not zeros."
        ),
    ),
    WorldBankMapping(
        indicator_code="SECONDARY_ENROLLMENT",
        external_code="SE.SEC.ENRR",
        external_name="School enrollment, secondary (% gross)",
        external_unit="% gross enrollment ratio",
        transform_notes=(
            "Gross enrollment ratio: total secondary enrollment regardless of "
            "age as % of the official secondary-school-age population. Can "
            "exceed 100. UNESCO UIS underlying; missing years are gaps."
        ),
    ),
    WorldBankMapping(
        indicator_code="TERTIARY_ENROLLMENT",
        external_code="SE.TER.ENRR",
        external_name="School enrollment, tertiary (% gross)",
        external_unit="% gross enrollment ratio",
        transform_notes=(
            "Gross enrollment ratio: total tertiary enrollment as % of the "
            "5-year age group following secondary school. Can exceed 100. "
            "UNESCO UIS underlying; missing years are gaps."
        ),
    ),
    WorldBankMapping(
        indicator_code="UNEMPLOYMENT_RATE",
        external_code="SL.UEM.TOTL.ZS",
        external_name="Unemployment, total (% of total labor force) (modeled ILO estimate)",
        external_unit="% of labor force",
        transform_notes=(
            "ILO modeled estimate, annual. National-definition series exist "
            "but are not cross-country comparable — the ILO modelled series "
            "is used deliberately."
        ),
    ),
    WorldBankMapping(
        indicator_code="REER_INDEX",
        external_code="PX.REX.REER",
        external_name="Real effective exchange rate index (2010 = 100)",
        external_unit="index",
        transform_notes=(
            "WB convention: rising index = real APPRECIATION = declining "
            "price competitiveness (opposite-sign intuition vs a "
            "depreciation-positive read). Annual; narrow-based index."
        ),
    ),
    WorldBankMapping(
        indicator_code="BROADBAND_PER_100",
        external_code="IT.NET.BBND.P2",
        external_name="Fixed broadband subscriptions (per 100 people)",
        external_unit="per 100 people",
        transform_notes="ITU via WDI, annual; coverage proxy only.",
    ),
    WorldBankMapping(
        indicator_code="FDI_NET_INFLOWS_GDP",
        external_code="BX.KLT.DINV.WD.GD.ZS",
        external_name="Foreign direct investment, net inflows (% of GDP)",
        external_unit="percent of GDP",
        transform_notes=(
            "BoP basis, annual. Negative values = net outflows/disinvestment. "
            "Capital-attraction input for trade_capital_flows research — "
            "not automatically 'stronger' (tax-haven FDI distorts)."
        ),
    ),
    WorldBankMapping(
        indicator_code="LABOUR_FORCE_PARTICIPATION_RATE",
        external_code="SL.TLF.CACT.ZS",
        external_name="Labor force participation rate, total (% of total population ages 15+) (modeled ILO estimate)",
        external_unit="percent",
        transform_notes=(
            "ILO modeled estimate, annual — the modeled series is used "
            "deliberately for cross-country comparability (national-definition "
            "series are not comparable)."
        ),
    ),
    WorldBankMapping(
        indicator_code="GOVERNMENT_EFFECTIVENESS_WGI_SCORE",
        external_code="GOV_WGI_GE_SC",
        external_name="Government Effectiveness - Governance score (0-100)",
        external_unit="score 0-100",
        transform_notes=(
            "WGI 2025-revision absolute governance score (0-100) for "
            "Government Effectiveness — quality of public services, civil "
            "service, policy formulation and implementation, credibility of "
            "the government's commitment to policies. Perception-based "
            "composite with measurement uncertainty — a source indicator, "
            "not an Atlas force score."
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
    WorldBankMapping(
        indicator_code="NATURAL_DISASTER_AFFECTED_PCT",
        external_code="EN.CLC.MDAT.ZS",
        external_name=(
            "Droughts, floods, extreme temperatures "
            "(% of population, average 1990-2009)"
        ),
        external_unit="% of population affected (annual average)",
        transform_notes=(
            "EM-DAT-derived structural exposure measure published by the World "
            "Bank at a single date (2009) covering the 1990-2009 average — NOT "
            "an annual time series and not an event count. Missing country "
            "values mean 'no published average', never 'zero events'."
        ),
    ),
    WorldBankMapping(
        indicator_code="GDP_PPP_CURRENT_INTL",
        external_code="NY.GDP.MKTP.PP.CD",
        external_name="GDP, PPP (current international $)",
        external_unit="current international $",
        transform_notes="PPP GDP in current international dollars; method/base-year specific — not mixed with other PPP bases.",
    ),
    WorldBankMapping(
        indicator_code="GDP_REAL_CONSTANT_USD",
        external_code="NY.GDP.MKTP.KD",
        external_name="GDP (constant 2015 US$)",
        external_unit="constant 2015 US$",
        transform_notes="Constant-price real GDP volume, fixed WDI 2015 base year.",
    ),
    WorldBankMapping(
        indicator_code="MERCHANDISE_EXPORTS_USD",
        external_code="TX.VAL.MRCH.CD.WT",
        external_name="Merchandise exports (current US$)",
        external_unit="current US$",
        transform_notes="Goods exports only; used for global goods-export share, never trade openness.",
    ),
    WorldBankMapping(
        indicator_code="MERCHANDISE_IMPORTS_USD",
        external_code="TM.VAL.MRCH.CD.WT",
        external_name="Merchandise imports (current US$)",
        external_unit="current US$",
        transform_notes="Goods imports only; used for global goods-import share, never trade openness.",
    ),
    WorldBankMapping(
        indicator_code="COMMERCIAL_SERVICE_EXPORTS_USD",
        external_code="TX.VAL.SERV.CD.WT",
        external_name="Commercial service exports (current US$)",
        external_unit="current US$",
        transform_notes="Commercial services excluding government services n.i.e.; separate from merchandise trade.",
    ),
    WorldBankMapping(
        indicator_code="COMMERCIAL_SERVICE_IMPORTS_USD",
        external_code="TM.VAL.SERV.CD.WT",
        external_name="Commercial service imports (current US$)",
        external_unit="current US$",
        transform_notes="Commercial services excluding government services n.i.e.; separate from merchandise trade.",
    ),
    WorldBankMapping(
        indicator_code="PATENT_APPLICATIONS_RESIDENT",
        external_code="IP.PAT.RESD",
        external_name="Patent applications, residents",
        external_unit="applications",
        transform_notes="WIPO via WDI resident filing count — innovation output proxy, not patent quality.",
    ),
    WorldBankMapping(
        indicator_code="PATENT_APPLICATIONS_NONRESIDENT",
        external_code="IP.PAT.NRES",
        external_name="Patent applications, nonresidents",
        external_unit="applications",
        transform_notes="WIPO via WDI non-resident filing count — foreign filing interest proxy, not domestic invention count.",
    ),
    WorldBankMapping(
        indicator_code="RESEARCHERS_PER_MILLION",
        external_code="SP.POP.SCIE.RD.P6",
        external_name="Researchers in R&D (per million people)",
        external_unit="per million people",
        transform_notes="UNESCO via WDI research-capacity density; not output or quality.",
    ),
    WorldBankMapping(
        indicator_code="HIGH_TECHNOLOGY_EXPORTS_USD",
        external_code="TX.VAL.TECH.CD",
        external_name="High-technology exports (current US$)",
        external_unit="current US$",
        transform_notes="WDI high-R&D-intensity product exports; trade-output proxy affected by assembly/classification.",
    ),
    WorldBankMapping(
        indicator_code="STOCK_MARKET_CAP_GDP",
        external_code="CM.MKT.LCAP.GD.ZS",
        external_name="Market capitalization of listed domestic companies (% of GDP)",
        external_unit="% of GDP",
        transform_notes="Domestic listed-market depth; not an international financial-centre score.",
    ),
    WorldBankMapping(
        indicator_code="DOMESTIC_CREDIT_PRIVATE_GDP",
        external_code="FS.AST.PRVT.GD.ZS",
        external_name="Domestic credit to private sector (% of GDP)",
        external_unit="% of GDP",
        transform_notes="Financial-system depth; separate from international banking and reserve status.",
    ),
    WorldBankMapping(
        indicator_code="BROAD_MONEY_GDP",
        external_code="FM.LBL.BMNY.GD.ZS",
        external_name="Broad money (% of GDP)",
        external_unit="% of GDP",
        transform_notes="Monetary-system depth; not reserve currency status or international intermediation.",
    ),
)

_MAPPING_BY_INDICATOR_CODE = {m.indicator_code: m for m in WORLD_BANK_MAPPINGS}
_MAPPING_BY_EXTERNAL_CODE = {m.external_code: m for m in WORLD_BANK_MAPPINGS}


def get_world_bank_mapping(indicator_code: str) -> WorldBankMapping | None:
    return _MAPPING_BY_INDICATOR_CODE.get(indicator_code)


def get_world_bank_mapping_by_external_code(external_code: str) -> WorldBankMapping | None:
    """Reverse lookup: World Bank series code → canonical indicator mapping."""
    return _MAPPING_BY_EXTERNAL_CODE.get(external_code)