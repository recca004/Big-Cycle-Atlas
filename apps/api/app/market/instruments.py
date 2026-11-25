"""Verified initial market instrument registry (Mission 5 §15-§16).

Every external_code was probed live against FRED fredgraph.csv on
2026-11-25 — codes that returned HTML errors were EXCLUDED, never
guessed. Known gaps are documented in `notes`, not filled with
fiction.

Provider: FRED (public fredgraph.csv, no API key).
Frequencies: daily (yields, FX, SP500, corp yields, ECB rate) or
monthly (OECD-sourced share-price indices, long-term yields, interbank
rates, FEDFUNDS, commodity index).

Return semantics (§17): yields and spreads are NOT returns; the OECD
share-price indices are price indices (dividends excluded); the
commodity index is a spot price index, NOT futures returns.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentSpec:
    code: str                    # canonical Atlas code
    name: str
    asset_class: str             # AssetClass value
    return_methodology: str      # ReturnMethodology value
    country_iso3: str | None     # None = global/multi-country
    currency: str
    unit: str
    frequency: str               # daily | monthly
    external_code: str           # FRED series id
    quote_convention: str | None = None
    notes: str | None = None


def _eq(iso3: str, name: str, ccy: str) -> InstrumentSpec:
    """OECD share-price index (2015=100), monthly — price index, no dividends."""
    return InstrumentSpec(
        code=f"{iso3}_EQUITY_PRICE_INDEX",
        name=f"{name} share price index (OECD, 2015=100)",
        asset_class="equity_index",
        return_methodology="price_index",
        country_iso3=iso3,
        currency=ccy,
        unit="index 2015=100",
        frequency="monthly",
        external_code=f"SPASTT01{iso3[:2]}M661N",
        notes="Price index — dividend-adjusted total return NOT available.",
    )


def _lt_yield(iso3: str, name: str, ext: str | None = None) -> InstrumentSpec:
    """Long-term government bond yield, monthly (OECD)."""
    return InstrumentSpec(
        code=f"{iso3}_GOV_10Y_YIELD",
        name=f"{name} 10Y government bond yield",
        asset_class="gov_bond_yield",
        return_methodology="yield_quote",
        country_iso3=iso3,
        currency="PCT",
        unit="percent per annum",
        frequency="monthly",
        external_code=ext or f"IRLTLT01{iso3[:2]}M156N",
        notes="Yield quote — bond total return requires duration modelling.",
    )


def _fx(code: str, name: str, ccy: str, conv: str, country: str | None) -> InstrumentSpec:
    return InstrumentSpec(
        code=code, name=name,
        asset_class="fx_rate",
        return_methodology="exchange_rate",
        country_iso3=country,
        currency=ccy, unit=conv, frequency="daily",
        external_code=_FX_CODES[code], quote_convention=conv,
    )


_FX_CODES = {
    "FX_USD_EUR": "DEXUSEU",   # USD per EUR
    "FX_USD_GBP": "DEXUSUK",   # USD per GBP
    "FX_CHF_USD": "DEXSZUS",   # CHF per USD
    "FX_JPY_USD": "DEXJPUS",   # JPY per USD
    "FX_CNY_USD": "DEXCHUS",   # CNY per USD
    "FX_INR_USD": "DEXINUS",   # INR per USD
}


INSTRUMENTS: list[InstrumentSpec] = [
    # --- Equities: OECD share-price indices, monthly, all 8 countries ---
    _eq("USA", "United States", "USD"),
    _eq("CHE", "Switzerland", "CHF"),
    _eq("DEU", "Germany", "EUR"),
    _eq("FRA", "France", "EUR"),
    _eq("GBR", "United Kingdom", "GBP"),
    _eq("JPN", "Japan", "JPY"),
    InstrumentSpec(  # CHN[:2] == CHE[:2] == "CH" — must be explicit
        code="CHN_EQUITY_PRICE_INDEX",
        name="China share price index (OECD, 2015=100)",
        asset_class="equity_index",
        return_methodology="price_index",
        country_iso3="CHN",
        currency="CNY",
        unit="index 2015=100",
        frequency="monthly",
        external_code="SPASTT01CNM661N",
        notes="Price index — dividend-adjusted total return NOT available.",
    ),
    _eq("IND", "India", "INR"),
    InstrumentSpec(
        code="US_SP500", name="S&P 500 index (daily)",
        asset_class="equity_index", return_methodology="price_index",
        country_iso3="USA", currency="USD", unit="index points",
        frequency="daily", external_code="SP500",
        notes="Price index — no dividends.",
    ),
    # --- Government bond yields ---
    _lt_yield("USA", "United States", "IRLTLT01USM156N"),
    _lt_yield("CHE", "Switzerland"),
    _lt_yield("DEU", "Germany"),
    _lt_yield("FRA", "France"),
    _lt_yield("GBR", "United Kingdom"),
    _lt_yield("JPN", "Japan"),
    _lt_yield("IND", "India", "INDIRLTLT01STM"),
    # CHN 10Y: no verified free FRED series — documented gap, not filled.
    InstrumentSpec(
        code="US_GOV_2Y_YIELD", name="US 2Y Treasury yield (daily)",
        asset_class="gov_bond_yield", return_methodology="yield_quote",
        country_iso3="USA", currency="PCT", unit="percent per annum",
        frequency="daily", external_code="DGS2"),
    InstrumentSpec(
        code="US_GOV_10Y_YIELD_D", name="US 10Y Treasury yield (daily)",
        asset_class="gov_bond_yield", return_methodology="yield_quote",
        country_iso3="USA", currency="PCT", unit="percent per annum",
        frequency="daily", external_code="DGS10"),
    InstrumentSpec(
        code="US_GOV_30Y_YIELD", name="US 30Y Treasury yield (daily)",
        asset_class="gov_bond_yield", return_methodology="yield_quote",
        country_iso3="USA", currency="PCT", unit="percent per annum",
        frequency="daily", external_code="DGS30"),
    # --- Cash / short rates ---
    InstrumentSpec(
        code="US_TBILL_3M", name="US 3-month T-bill secondary market rate",
        asset_class="cash_rate", return_methodology="yield_quote",
        country_iso3="USA", currency="PCT", unit="percent per annum",
        frequency="daily", external_code="DTB3"),
    InstrumentSpec(
        code="US_FEDFUNDS", name="US effective federal funds rate",
        asset_class="policy_rate", return_methodology="policy_rate_quote",
        country_iso3="USA", currency="PCT", unit="percent per annum",
        frequency="monthly", external_code="FEDFUNDS"),
    InstrumentSpec(
        code="EA_ECB_DEPOSIT_RATE", name="ECB deposit facility rate",
        asset_class="policy_rate", return_methodology="policy_rate_quote",
        country_iso3=None, currency="PCT", unit="percent per annum",
        frequency="daily", external_code="ECBDFR",
        notes="Euro-area policy rate — covers DEU/FRA exposure."),
    InstrumentSpec(
        code="GB_POLICY_RATE", name="UK immediate rate (<24h), monthly",
        asset_class="policy_rate", return_methodology="policy_rate_quote",
        country_iso3="GBR", currency="PCT", unit="percent per annum",
        frequency="monthly", external_code="IRSTCI01GBM156N"),
    InstrumentSpec(
        code="JP_POLICY_RATE", name="Japan immediate rate (<24h), monthly",
        asset_class="policy_rate", return_methodology="policy_rate_quote",
        country_iso3="JPN", currency="PCT", unit="percent per annum",
        frequency="monthly", external_code="IRSTCI01JPM156N"),
    InstrumentSpec(
        code="CH_POLICY_RATE", name="Switzerland immediate rate (<24h), monthly",
        asset_class="policy_rate", return_methodology="policy_rate_quote",
        country_iso3="CHE", currency="PCT", unit="percent per annum",
        frequency="monthly", external_code="IRSTCI01CHM156N"),
    InstrumentSpec(
        code="DE_INTERBANK_3M", name="Germany 3-month interbank rate",
        asset_class="cash_rate", return_methodology="yield_quote",
        country_iso3="DEU", currency="PCT", unit="percent per annum",
        frequency="monthly", external_code="IR3TIB01DEM156N"),
    # --- Corporate bonds ---
    InstrumentSpec(
        code="US_CORP_MASTER_YIELD", name="ICE BofA US Corporate Master effective yield",
        asset_class="corporate_bond_yield", return_methodology="yield_quote",
        country_iso3="USA", currency="PCT", unit="percent per annum",
        frequency="daily", external_code="BAMLC0A0CMEY",
        notes="Effective yield — index total return needs duration modelling."),
    InstrumentSpec(
        code="US_HY_YIELD", name="ICE BofA US High Yield effective yield",
        asset_class="corporate_bond_yield", return_methodology="yield_quote",
        country_iso3="USA", currency="PCT", unit="percent per annum",
        frequency="daily", external_code="BAMLH0A0HYM2EY"),
    # --- FX (for §24 base-currency conversion) ---
    _fx("FX_USD_EUR", "US dollar per euro", "USD", "USD per EUR", "FRA"),
    _fx("FX_USD_GBP", "US dollar per pound", "USD", "USD per GBP", "GBR"),
    _fx("FX_CHF_USD", "Swiss franc per US dollar", "CHF", "CHF per USD", "CHE"),
    _fx("FX_JPY_USD", "Japanese yen per US dollar", "JPY", "JPY per USD", "JPN"),
    _fx("FX_CNY_USD", "Chinese yuan per US dollar", "CNY", "CNY per USD", "CHN"),
    _fx("FX_INR_USD", "Indian rupee per US dollar", "INR", "INR per USD", "IND"),
    # --- Commodities ---
    InstrumentSpec(
        code="COMMODITY_ALL_INDEX", name="Global price index, all commodities (IMF)",
        asset_class="commodity_index", return_methodology="spot_price",
        country_iso3=None, currency="USD", unit="index 2016=100",
        frequency="monthly", external_code="PALLFNFINDEXM",
        notes="Spot price index — NOT futures returns. No free daily gold "
              "series verified on FRED (documented gap)."),
]


INSTRUMENT_BY_CODE = {i.code: i for i in INSTRUMENTS}
