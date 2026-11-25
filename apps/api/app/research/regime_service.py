"""Regime history service (Mission 5 §22, §25).

Pulls the macro growth/inflation inputs (latest vintage — retrospective,
backtest_safe=False) plus market financial-conditions measurements, runs
the regime classifier, and joins regime years to equity-index returns.
"""
from __future__ import annotations

import statistics
from datetime import date

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Country,
    Indicator,
    MarketInstrument,
    MarketObservation,
    Observation,
)
from app.research.regime import (
    FinancialConditions,
    RegimeConfig,
    RegimeYear,
    classify_years,
)

# country -> instrument codes for §21 measurements
_POLICY_RATE = {
    "USA": "US_FEDFUNDS", "GBR": "GB_POLICY_RATE", "JPN": "JP_POLICY_RATE",
    "CHE": "CH_POLICY_RATE", "DEU": "EA_ECB_DEPOSIT_RATE",
    "FRA": "EA_ECB_DEPOSIT_RATE",
}
_LONG_YIELD = {
    "USA": "USA_GOV_10Y_YIELD", "CHE": "CHE_GOV_10Y_YIELD",
    "DEU": "DEU_GOV_10Y_YIELD", "FRA": "FRA_GOV_10Y_YIELD",
    "GBR": "GBR_GOV_10Y_YIELD", "JPN": "JPN_GOV_10Y_YIELD",
    "IND": "IND_GOV_10Y_YIELD",
}
_EQUITY = {iso3: f"{iso3}_EQUITY_PRICE_INDEX" for iso3 in
           ("USA", "CHE", "DEU", "FRA", "GBR", "JPN", "CHN", "IND")}
_FX = {
    "CHE": "FX_CHF_USD", "JPN": "FX_JPY_USD", "CHN": "FX_CNY_USD",
    "IND": "FX_INR_USD", "GBR": "FX_USD_GBP", "DEU": "FX_USD_EUR",
    "FRA": "FX_USD_EUR",
}


async def _annual_macro(
    session: AsyncSession, country_id: int, code: str
) -> dict[int, float]:
    """Latest-vintage annual values for an indicator, keyed by year."""
    rows = (
        await session.execute(
            select(Observation.period_start, Observation.value)
            .join(Indicator, Indicator.id == Observation.indicator_id)
            .where(
                Observation.country_id == country_id,
                Indicator.code == code,
            )
            .order_by(Observation.period_start, Observation.vintage_number.desc())
        )
    ).all()
    out: dict[int, float] = {}
    for period_start, value in rows:
        if period_start is None:
            continue
        y = period_start.year
        if y not in out:  # first row per year = highest vintage (desc order)
            out[y] = value
    return out


async def _annual_market_mean(
    session: AsyncSession, code: str
) -> dict[int, float]:
    """Annual mean of a market series (monthly/daily -> year)."""
    rows = (
        await session.execute(
            select(
                extract("year", MarketObservation.obs_date),
                func.avg(MarketObservation.value),
            )
            .join(
                MarketInstrument,
                MarketInstrument.id == MarketObservation.instrument_id,
            )
            .where(MarketInstrument.code == code)
            .group_by(extract("year", MarketObservation.obs_date))
        )
    ).all()
    return {int(y): v for y, v in rows}


async def _annual_market_last(
    session: AsyncSession, code: str
) -> dict[int, float]:
    """Year-end value of a market series (last obs in each year)."""
    rows = (
        await session.execute(
            select(MarketObservation.obs_date, MarketObservation.value)
            .join(
                MarketInstrument,
                MarketInstrument.id == MarketObservation.instrument_id,
            )
            .where(MarketInstrument.code == code)
            .order_by(MarketObservation.obs_date)
        )
    ).all()
    out: dict[int, float] = {}
    for d, v in rows:
        out[d.year] = v  # later dates overwrite -> year-end value
    return out


async def regime_history(
    session: AsyncSession, iso3: str
) -> dict | None:
    country = (
        await session.execute(select(Country).where(Country.iso3 == iso3))
    ).scalar_one_or_none()
    if country is None:
        return None

    gdp = await _annual_macro(session, country.id, "GDP_GROWTH")
    cpi = await _annual_macro(session, country.id, "INFLATION_CPI")
    cfg = RegimeConfig()
    years: list[RegimeYear] = classify_years(gdp, cpi, cfg)

    # §21 financial conditions per year (annual means / year-end FX change)
    policy = (
        await _annual_market_mean(session, _POLICY_RATE[iso3])
        if iso3 in _POLICY_RATE else {}
    )
    ly = (
        await _annual_market_mean(session, _LONG_YIELD[iso3])
        if iso3 in _LONG_YIELD else {}
    )
    fx = (
        await _annual_market_last(session, _FX[iso3])
        if iso3 in _FX else {}
    )
    financial = []
    for y in sorted(set(policy) | set(ly) | set(fx)):
        fx_ret = (
            fx[y] / fx[y - 1] - 1.0
            if fx.get(y) is not None and fx.get(y - 1) not in (None, 0)
            else None
        )
        real_rate = (
            policy[y] - cpi[y]
            if policy.get(y) is not None and cpi.get(y) is not None
            else None
        )
        missing = tuple(
            n for n, v in (("policy_rate", policy.get(y)),
                           ("long_yield", ly.get(y)),
                           ("currency_return", fx_ret))
            if v is None
        )
        financial.append(FinancialConditions(
            year=y,
            policy_rate=policy.get(y),
            long_yield=ly.get(y),
            real_rate_proxy=real_rate,
            currency_return=fx_ret,
            missing=missing,
        ))

    return {
        "country": iso3,
        "model_id": cfg.model_id,
        "model_version": cfg.version,
        "methodology_status": "experimental",
        "execution_mode": "retrospective_latest_vintage",
        "backtest_safe": False,
        "assumptions": {
            "growth_eps_pp": cfg.growth_eps,
            "inflation_eps_pp": cfg.inflation_eps,
            "cadence": "annual (macro inputs are annual)",
            "note": "thresholds are model assumptions, not universal laws",
        },
        "regimes": [
            {
                "year": r.year,
                "regime": r.regime.value,
                "growth_direction": r.growth_direction.value,
                "inflation_direction": r.inflation_direction.value,
                "gdp_growth": r.gdp_growth,
                "inflation_cpi": r.inflation,
                "missing_inputs": list(r.missing_inputs),
                "reason": r.reason,
            }
            for r in years
        ],
        "financial_conditions": [
            {
                "year": f.year,
                "policy_rate": f.policy_rate,
                "long_yield": f.long_yield,
                "real_rate_proxy": f.real_rate_proxy,
                "currency_return": f.currency_return,
                "missing": list(f.missing),
            }
            for f in financial
        ],
        "coverage": {
            "gdp_years": len(gdp),
            "cpi_years": len(cpi),
            "policy_rate_years": len(policy),
            "long_yield_years": len(ly),
            "classified": sum(
                1 for r in years if r.regime.value != "UNCLASSIFIED"
            ),
        },
        "limitations": [
            "annual macro cadence — monthly regime claims not supported",
            "retrospective latest-vintage inputs — NOT historically actionable",
            "financial conditions are separate measurements, not an index",
        ],
    }


async def regime_asset_returns(
    session: AsyncSession, iso3: str
) -> dict | None:
    """§25: equity-index annual returns bucketed by regime year.

    Correlation framing only — small samples, no causation claims.
    """
    hist = await regime_history(session, iso3)
    if hist is None:
        return None
    code = _EQUITY.get(iso3)
    if code is None:
        return None
    eq = await _annual_market_last(session, code)
    returns = {
        y: eq[y] / eq[y - 1] - 1.0
        for y in sorted(eq) if y - 1 in eq and eq[y - 1]
    }
    buckets: dict[str, list[float]] = {}
    for r in hist["regimes"]:
        ret = returns.get(r["year"])
        if ret is None or r["regime"] == "UNCLASSIFIED":
            continue
        buckets.setdefault(r["regime"], []).append(ret)

    return {
        "country": iso3,
        "instrument": code,
        "model_version": hist["model_version"],
        "methodology_status": "experimental",
        "by_regime": {
            regime: {
                "episodes": len(vals),
                "mean_annual_return": statistics.mean(vals),
                "min": min(vals),
                "max": max(vals),
            }
            for regime, vals in buckets.items()
        },
        "warning": (
            "Retrospective regime labels on latest-vintage data joined to "
            "annual price-index returns — association, NOT causation; "
            "episode counts are too small for inference and nothing here "
            "is a historically actionable signal."
        ),
    }
