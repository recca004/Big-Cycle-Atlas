"""Debt & monetary cycle research module (Workstream C).

Assembles actual measured series — never combined into a single unsupported
debt-cycle stage score — for /research/debt-cycle and related research routes.
All series keep source, unit and measurement definitions attached; derived
estimates are labelled as such.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Country, CrisisEvent, Indicator, Observation, ResearchObservation,
)

_COUNTRY_FK = Country.iso3

PRIMARY_ENTITIES = ("USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND")
JST_ENTITIES = ("AUS", "BEL", "CAN", "CHE", "DEU", "DNK", "ESP", "FIN", "FRA",
                "GBR", "IRL", "ITA", "JPN", "NLD", "NOR", "PRT", "SWE", "USA")

# --- BIS sectoral credit (WS_TC_CBPOL) ---------------------------------------
BIS_SECTOR_VARS = {
    "CREDIT_GOVT_NOMINAL_GDP": "General government credit, nominal valuation (% of GDP)",
    "CREDIT_GOVT_MARKET_GDP": "General government credit, market valuation (% of GDP)",
    "CREDIT_PRIVATE_NF_GDP": "Private non-financial sector credit (% of GDP)",
    "CREDIT_HOUSEHOLDS_GDP": "Household credit (% of GDP)",
    "CREDIT_CORP_NF_GDP": "Non-financial corporate credit (% of GDP)",
    "POLICY_RATE_PCT": "Central bank policy rate (%)",
}
BIS_SOURCE = {"source_key": "bis_credit_policy", "dataset_version": "WS_TC_CBPOL",
              "publisher": "Bank for International Settlements"}
JST_SOURCE = {"source_key": "jst_macrohistory", "dataset_version": "R6",
              "publisher": "Jorda-Schularick-Taylor Macrohistory Database"}

# Canonical indicators used for the modern 8-country panel.
CANONICAL_DEBT = {
    "GOVERNMENT_DEBT_GDP": "General government gross debt (% of GDP, IMF WEO)",
    "DEBT_SERVICE_RATIO": "BIS private-sector debt service ratio (% of income)",
    "CREDIT_TO_GDP_GAP": "BIS credit-to-GDP gap (percentage points)",
    "DOMESTIC_CREDIT_PRIVATE_GDP": "Domestic credit to private sector (% of GDP, WDI)",
    "BROAD_MONEY_GDP": "Broad money (% of GDP, WDI)",
    "INFLATION_CPI": "Consumer price inflation (annual %, WDI)",
    "REER_INDEX": "Real effective exchange rate index (BIS/WDI)",
}
CANONICAL_SOURCE = {"source_key": "canonical_indicator", "dataset_version": "latest",
                    "publisher": "World Bank WDI / IMF WEO / BIS"}


def _period_label(start: datetime) -> str:
    y, m = start.year, start.month
    return f"{y}" if m == 1 else f"{y}-Q{(m - 1) // 3 + 1}"


async def _research_series(
    session: AsyncSession, source_key: str, variables: Iterable[str],
    entities: Iterable[str] | None = None,
) -> dict[str, dict[str, list[list[Any]]]]:
    q = select(
        ResearchObservation.entity_code, ResearchObservation.variable_code,
        ResearchObservation.period_start, ResearchObservation.value,
    ).where(
        ResearchObservation.source_key == source_key,
        ResearchObservation.variable_code.in_(list(variables)),
    ).order_by(ResearchObservation.period_start)
    if entities:
        q = q.where(ResearchObservation.entity_code.in_(list(entities)))
    out: dict[str, dict[str, list[list[Any]]]] = defaultdict(lambda: defaultdict(list))
    for ent, var, start, val in (await session.execute(q)).all():
        out[ent][var].append([_period_label(start), val])
    return out


async def _canonical_series(
    session: AsyncSession, codes: Iterable[str], entities: Iterable[str],
) -> dict[str, dict[str, list[list[Any]]]]:
    rows = (await session.execute(
        select(Observation, Indicator.code, Country.iso3)
        .join(Indicator, Observation.indicator_id == Indicator.id)
        .join(Country, Observation.country_id == Country.id)
        .where(Indicator.code.in_(list(codes)),
               Country.iso3.in_(list(entities)))
        .order_by(Observation.period_start)
    )).all()
    out: dict[str, dict[str, list[list[Any]]]] = defaultdict(lambda: defaultdict(list))
    for obs, code, iso3 in rows:
        out[iso3][code].append([_period_label(obs.period_start), obs.value])
    return out


def _ratio_series(panel: dict[str, dict[str, float]], num: str, den: str) -> list[list[Any]]:
    """Derive a ratio time series from two JST variables keyed {year: value}."""
    out = []
    for year, n in sorted(panel.get(num, {}).items()):
        d = panel.get(den, {}).get(year)
        if d not in (None, 0):
            out.append([str(year), n / d])
    return out


def _series_meta(label: str, unit: str, source: dict[str, str],
                 frequency: str = "annual", derived: bool = False,
                 methodology: str | None = None) -> dict[str, Any]:
    return {
        "label": label, "unit": unit, "source": source,
        "frequency": frequency, "derived_estimate": derived,
        "methodology": methodology,
    }


async def _jst_entity_panel(session: AsyncSession, entity: str,
                            variables: Iterable[str]) -> dict[str, dict[str, float]]:
    rows = (await session.execute(
        select(ResearchObservation.variable_code, ResearchObservation.period_start,
               ResearchObservation.value)
        .where(ResearchObservation.source_key == "jst_macrohistory",
               ResearchObservation.entity_code == entity,
               ResearchObservation.variable_code.in_(list(variables)))
    )).all()
    panel: dict[str, dict[str, float]] = defaultdict(dict)
    for var, start, val in rows:
        panel[var][start.year] = val
    return panel


async def debt_cycle_overview(
    session: AsyncSession, entities: list[str] | None = None,
) -> dict[str, Any]:
    entities = entities or list(PRIMARY_ENTITIES)
    # Which datasets actually cover each entity.
    bis_rows = await _research_series(
        session, "bis_credit_policy", BIS_SECTOR_VARS.keys(), entities)
    canonical = await _canonical_series(session, CANONICAL_DEBT.keys(), entities)

    jst_vars = ("debtgdp", "tloans", "thh", "tbus", "tmort", "gdp", "stir",
                "ltrate", "cpi", "money", "narrowm", "xrusd", "expenditure",
                "revenue", "ca", "peg")
    crises = (await session.execute(
        select(CrisisEvent.entity_code, CrisisEvent.start_period,
               CrisisEvent.event_type, CrisisEvent.source_key,
               CrisisEvent.dataset_version)
        .where(CrisisEvent.entity_code.in_(entities),
               CrisisEvent.event_type == "banking_crisis")
        .order_by(CrisisEvent.start_period)
    )).all()

    sections: dict[str, dict[str, dict[str, Any]]] = {
        "sectoral_credit": {}, "monetary_conditions": {},
        "fiscal_conditions": {},
    }
    for ent in entities:
        sectoral: dict[str, Any] = {}
        for var, label in BIS_SECTOR_VARS.items():
            pts = bis_rows.get(ent, {}).get(var, [])
            if pts:
                sectoral[var] = {"meta": _series_meta(
                    label, "% of GDP" if var != "POLICY_RATE_PCT" else "percent",
                    BIS_SOURCE, "quarterly"), "points": pts}
        for code, label in CANONICAL_DEBT.items():
            pts = canonical.get(ent, {}).get(code, [])
            if pts:
                sectoral[code] = {"meta": _series_meta(label, "% of GDP", CANONICAL_SOURCE),
                                  "points": pts}

        monetary: dict[str, Any] = {}
        fiscal: dict[str, Any] = {}
        if ent in JST_ENTITIES:
            panel = await _jst_entity_panel(session, ent, jst_vars)
            pts = [[str(y), v] for y, v in sorted(panel.get("debtgdp", {}).items())]
            if pts:
                sectoral["debtgdp"] = {"meta": _series_meta(
                    "Public debt / GDP (JST)", "ratio of GDP", JST_SOURCE), "points": pts}
            # Derived sectoral ratios — labelled derived, not official series.
            for name, num, den, label in (
                ("jst_tloans_gdp", "tloans", "gdp", "Private bank loans / GDP (derived from JST tloans ÷ gdp)"),
                ("jst_thh_gdp", "thh", "gdp", "Household loans / GDP (derived from JST thh ÷ gdp)"),
                ("jst_tbus_gdp", "tbus", "gdp", "Business loans / GDP (derived from JST tbus ÷ gdp)"),
                ("jst_tmort_gdp", "tmort", "gdp", "Mortgage loans / GDP (derived from JST tmort ÷ gdp)"),
            ):
                pts = _ratio_series(panel, num, den)
                if pts:
                    sectoral[name] = {"meta": _series_meta(
                        label, "ratio of GDP", JST_SOURCE, derived=True,
                        methodology="tloans|thh|tbus|tmort divided by nominal gdp, same source"), "points": pts}

            # Monetary conditions.
            for var, label, unit in (
                ("stir", "Short-term interest rate", "percent"),
                ("ltrate", "Long-term interest rate", "percent"),
                ("xrusd", "Exchange rate vs USD (log)", "log units"),
                ("money", "Broad money (nominal)", "LC billions"),
            ):
                pts = [[str(y), v] for y, v in sorted(panel.get(var, {}).items())]
                if pts:
                    monetary[f"jst_{var}"] = {"meta": _series_meta(label, unit, JST_SOURCE), "points": pts}
            # Real long-term rate = ltrate - CPI YoY inflation.
            real_ltr: list[list[Any]] = []
            years = sorted(panel.get("ltrate", {}))
            cpi = panel.get("cpi", {})
            for y in years:
                prev = cpi.get(y - 1)
                if prev not in (None, 0) and cpi.get(y) is not None:
                    infl = (cpi[y] / prev - 1.0) * 100.0
                    real_ltr.append([str(y), panel["ltrate"][y] - infl])
            if real_ltr:
                monetary["real_ltrate_derived"] = {"meta": _series_meta(
                    "Real long-term rate (ltrate - CPI inflation, derived)", "percent",
                    JST_SOURCE, derived=True,
                    methodology="JST ltrate minus year-over-year CPI growth"), "points": real_ltr}
            pts = _ratio_series(panel, "money", "gdp")
            if pts:
                monetary["jst_money_gdp"] = {"meta": _series_meta(
                    "Broad money / GDP (derived)", "ratio of GDP", JST_SOURCE,
                    derived=True, methodology="JST money ÷ gdp"), "points": pts}

            # Fiscal conditions — revenue/expenditure are nominal local currency.
            for name, num, den, label in (
                ("jst_revenue_gdp", "revenue", "gdp", "General government revenue / GDP (derived)"),
                ("jst_expenditure_gdp", "expenditure", "gdp", "General government expenditure / GDP (derived)"),
            ):
                pts = _ratio_series(panel, num, den)
                if pts:
                    fiscal[name] = {"meta": _series_meta(
                        label, "ratio of GDP", JST_SOURCE, derived=True,
                        methodology="JST nominal aggregate ÷ nominal gdp"), "points": pts}
            rev, exp = panel.get("revenue", {}), panel.get("expenditure", {})
            bal = [[str(y), (rev[y] - exp[y]) / panel["gdp"][y]]
                   for y in sorted(set(rev) & set(exp) & set(panel.get("gdp", {})))
                   if panel["gdp"][y] != 0]
            if bal:
                fiscal["jst_fiscal_balance_gdp"] = {"meta": _series_meta(
                    "Fiscal balance proxy (revenue - expenditure) / GDP (derived)",
                    "ratio of GDP", JST_SOURCE, derived=True,
                    methodology="(JST revenue - JST expenditure) ÷ nominal gdp — total balance proxy, not a primary balance"), "points": bal}
            interest = []
            debt, lt = panel.get("debtgdp", {}), panel.get("ltrate", {})
            for y in sorted(set(debt) & set(lt)):
                interest.append([str(y), debt[y] * lt[y] / 100.0])
            if interest:
                fiscal["jst_interest_burden_estimate"] = {"meta": _series_meta(
                    "Public interest burden estimate (debt/GDP x long rate, derived)",
                    "ratio of GDP", JST_SOURCE, derived=True,
                    methodology="debtgdp(t) x ltrate(t)/100 — modelled estimate, NOT an official interest-expenditure series"), "points": interest}

        if sectoral:
            sections["sectoral_credit"][ent] = sectoral
        if monetary:
            sections["monetary_conditions"][ent] = monetary
        if fiscal:
            sections["fiscal_conditions"][ent] = fiscal

    crisis_overlay: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ent, start, etype, sk, dv in crises:
        crisis_overlay[ent].append({
            "year": start.year, "event_type": etype,
            "source_key": sk, "dataset_version": dv,
        })

    return {
        "module": "debt_monetary_cycle",
        "entities": entities,
        "entity_coverage_notes": {
            "jst": "JST R6 covers 18 advanced economies only (no CHN/IND); BIS sectoral credit covers the 8 primary countries + EUR",
        },
        "sections": sections,
        "crisis_overlay": dict(crisis_overlay),
        "methodology": [
            "All series are actual measured observations; nothing is combined into a single debt-cycle stage score.",
            "Derived ratios/estimates are flagged derived_estimate=true with explicit formulas.",
            "Real rates = nominal rate minus contemporaneous CPI YoY inflation (JST retrospective).",
            "Retrospective data only — not release-date-safe; strict_eligible scored periods remain 0.",
            "JST covers advanced economies only; CHN and IND appear through BIS/canonical modern series only.",
        ],
        "sources": {"bis": BIS_SOURCE, "jst": JST_SOURCE, "canonical": CANONICAL_SOURCE},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


COFER_AUX_NOTES = {
    "COFER_IMPUTED_SHARE_PCT": ("TFXRA_IMP — imputed allocated reserves share: IMF reallocates "
                              "'unallocated' reserves across currencies for reporting; an IMF "
                              "constructed estimate, not a reported share."),
}
FX_200PCT_NOTE = ("BIS FX turnover is measured per currency LEG; all legs sum to 200% "
                  "(two sides per transaction). Shares below are NOT normalised to 100% — "
                  "normalising would change the measure.")
EUR_NOTE = ("EUR is the shared Eurosystem currency area. Euro-area shares are never "
            "attributed to DEU or FRA individually.")


async def currency_power_overview(session: AsyncSession) -> dict[str, Any]:
    reserves = await _research_series(
        session, "imf_cofer",
        ("COFER_RESERVE_SHARE_PCT", "COFER_IMPUTED_SHARE_PCT", "COFER_RESERVE_CLAIMS_USD"))
    fx = await _research_series(
        session, "bis_fx_turnover",
        ("FX_TURNOVER_SHARE_200PCT", "FX_TURNOVER_DAILY_USD_MN"))
    lbs = await _research_series(
        session, "bis_lbs",
        ("LBS_CROSS_BORDER_CLAIMS_SHARE_PCT", "LBS_CROSS_BORDER_CLAIMS_USD_MN",
         "LBS_REPORTING_CLAIMS_SHARE_PCT", "LBS_REPORTING_CLAIMS_USD_MN"))

    def pack(rows, var, label, unit, src):
        out = {}
        for ent, series in rows.items():
            if series.get(var):
                out[ent] = {"meta": _series_meta(label, unit, src, "quarterly"),
                            "points": series[var]}
        return out

    cofer_src = {"source_key": "imf_cofer", "dataset_version": "COFER-SDMX-2.1",
                 "publisher": "IMF Currency Composition of Official FX Reserves"}
    fx_src = {"source_key": "bis_fx_turnover", "dataset_version": "WS_DER_OTC_TOV",
              "publisher": "BIS Triennial Central Bank Survey"}
    lbs_src = {"source_key": "bis_lbs", "dataset_version": "WS_LBS_D_PUB",
               "publisher": "BIS Locational Banking Statistics"}

    currency_ents = {e for e in lbs if e in ("USD", "EUR", "JPY", "GBP", "CHF", "ALL_CURRENCIES")}
    centre_ents = {e for e in lbs if e not in currency_ents}

    return {
        "module": "currency_power_monitor",
        "reserve_currency_shares": {
            "share_pct": pack(reserves, "COFER_RESERVE_SHARE_PCT",
                              "Official FX reserve share", "percent of allocated reserves", cofer_src),
            "imputed_share_pct": pack(reserves, "COFER_IMPUTED_SHARE_PCT",
                                      "Imputed share incl. unallocated reallocation", "percent of total reserves", cofer_src),
            "claims_usd": pack(reserves, "COFER_RESERVE_CLAIMS_USD",
                               "Official FX reserve claims", "USD millions", cofer_src),
        },
        "fx_turnover_shares": {
            "share_200pct": pack(fx, "FX_TURNOVER_SHARE_200PCT",
                                 "FX turnover share (per currency leg)", "percent of 200% total", fx_src),
            "daily_usd_mn": pack(fx, "FX_TURNOVER_DAILY_USD_MN",
                                 "Daily FX turnover", "USD millions/day", fx_src),
        },
        "banking_claims_by_currency": {
            "share_pct": pack({e: lbs[e] for e in currency_ents}, "LBS_CROSS_BORDER_CLAIMS_SHARE_PCT",
                              "Cross-border bank claims by currency", "percent", lbs_src),
            "usd_mn": pack({e: lbs[e] for e in currency_ents}, "LBS_CROSS_BORDER_CLAIMS_USD_MN",
                           "Cross-border bank claims by currency", "USD millions", lbs_src),
        },
        "financial_centres": {
            "share_pct": pack({e: lbs[e] for e in centre_ents}, "LBS_REPORTING_CLAIMS_SHARE_PCT",
                              "Reporting-centre cross-border claims share", "percent", lbs_src),
            "usd_mn": pack({e: lbs[e] for e in centre_ents}, "LBS_REPORTING_CLAIMS_USD_MN",
                           "Reporting-centre cross-border claims", "USD millions", lbs_src),
        },
        "methodology": [
            EUR_NOTE,
            FX_200PCT_NOTE,
            COFER_AUX_NOTES["COFER_IMPUTED_SHARE_PCT"],
            "INR is measured only in BIS FX turnover — COFER reserve shares are not reported for INR and are left unavailable, not imputed.",
            "Banking-office location (LBS reporting centre) is NOT total national financial influence — it measures where cross-border claims are booked.",
            "COFER methodology breaks (incl. euro introduction 1999) are recorded on the series, not smoothed.",
        ],
        "historical_currency_support": ["DEM", "FRF", "NLG", "ECU"],
        "sources": {"cofer": cofer_src, "fx": fx_src, "lbs": lbs_src},
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


HISTORICAL_PERIODS = (1500, 1700, 1820, 1900, 1950, 1980)
PWT_VARS = {
    "PWT_GDP_PER_WORKER_PPP2021": "Output per worker (2021 PPP USD)",
    "PWT_GDP_PER_HOUR_PPP2021": "Output per hour worked (2021 PPP USD)",
    "PWT_HUMAN_CAPITAL_INDEX": "Human capital index",
    "PWT_CAPITAL_STOCK_CONST2021_MN": "Capital stock (constant 2021, mn)",
    "PWT_RTFPNA_2021_1": "Total factor productivity (2021=1)",
    "PWT_CTFP_USA1": "TFP relative to USA (USA=1)",
}
ENTITY_DEFINITION_NOTES = {
    "DEU": "Maddison/PWT 'Germany' aggregates the territory within present-day borders; it does NOT equal a single continuous historical state (Prussia, German Empire, FRG/DRG eras differ).",
    "CHN": "Territory of present-day China; imperial dynastic GDP estimates are reconstructions, not national accounts.",
    "IND": "Territory of present-day India; pre-1947 figures refer to the colonial/subcontinental territory as defined by Maddison, not the Republic of India.",
    "GBR": "United Kingdom territory; pre-1801 Great Britain and empire colonies are NOT included.",
    "NLD": "Netherlands; Dutch empire (East Indies) output is excluded — metropolitan territory only.",
    "ITA": "Present-day Italy; pre-1861 states aggregated at territory level.",
    "USA": "United States territory.",
    "JPN": "Japan territory.",
}


async def historical_power_overview(session: AsyncSession) -> dict[str, Any]:
    mad = await _research_series(session, "maddison",
                                 ("MPD_GDPPC_2011INTL", "MPD_POP_THOUSANDS"))
    pwt = await _research_series(session, "pwt", PWT_VARS.keys())

    maddison_out: dict[str, dict[str, Any]] = {}
    panel_gdp: dict[int, dict[str, float]] = defaultdict(dict)
    for ent, series in sorted(mad.items()):
        gdppc = {int(p[0]): p[1] for p in series.get("MPD_GDPPC_2011INTL", [])}
        pop = {int(p[0]): p[1] for p in series.get("MPD_POP_THOUSANDS", [])}
        gdp_mn: dict[int, float] = {}
        for y in sorted(set(gdppc) & set(pop)):
            gdp_mn[y] = gdppc[y] * pop[y] / 1000.0  # thousands -> mn intl $
            panel_gdp[y][ent] = gdp_mn[y]
        maddison_out[ent] = {
            "gdppc_2011intl": {"meta": _series_meta(
                "GDP per capita (2011 international $)", "2011 intl $",
                {"source_key": "maddison", "dataset_version": "2023",
                 "publisher": "Maddison Project Database (Bolt & van Zanden, GGDC)"}),
                "points": [[str(y), v] for y, v in sorted(gdppc.items())]},
            "pop_thousands": {"meta": _series_meta(
                "Population", "thousands",
                {"source_key": "maddison", "dataset_version": "2023",
                 "publisher": "Maddison Project Database"}),
                "points": [[str(y), v] for y, v in sorted(pop.items())]},
            "gdp_level_mn_2011intl": {"meta": _series_meta(
                "Total GDP estimate (GDPpc x population, derived)", "mn 2011 intl $",
                {"source_key": "maddison", "dataset_version": "2023",
                 "publisher": "Maddison Project Database"}, derived=True,
                methodology="MPD_GDPPC_2011INTL x MPD_POP_THOUSANDS / 1000"),
                "points": [[str(y), v] for y, v in sorted(gdp_mn.items())]},
        }

    # Share of the imported 20-entity panel — NOT a world share.
    panel_share: dict[str, list[list[Any]]] = defaultdict(list)
    for y, ent_gdp in sorted(panel_gdp.items()):
        total = sum(ent_gdp.values())
        if total:
            for ent, v in ent_gdp.items():
                panel_share[ent].append([str(y), v / total * 100.0])

    pwt_src = {"source_key": "pwt", "dataset_version": "11.0",
               "publisher": "Penn World Table 11.0 (Feenstra, Inklaar & Timmer, GGDC)"}
    pwt_out = {}
    for ent, series in sorted(pwt.items()):
        pwt_out[ent] = {var: {"meta": _series_meta(PWT_VARS[var], "index/level", pwt_src),
                              "points": pts}
                        for var, pts in series.items() if pts}

    return {
        "module": "historical_power",
        "maddison": maddison_out,
        "panel_share_pct_of_20_entities": dict(panel_share),
        "pwt_productivity": pwt_out,
        "research_periods": list(HISTORICAL_PERIODS),
        "entity_definition_notes": ENTITY_DEFINITION_NOTES,
        "methodology": [
            "Sparse historical benchmark years are shown as observations only — no interpolation across gaps.",
            "Panel share = entity GDP divided by the sum of the 20 imported entities in the same year; it is NOT a world share.",
            "Modern country codes do NOT represent historical empires; per-entity territorial notes are attached.",
            "GDP estimates stay separate from military, trade, institutional and monetary influence — no composite empire-strength score.",
            "PWT productivity measures are kept separate (worker vs hour, capital, human capital, TFP) and do not replace the approved OECD-relative force method.",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
