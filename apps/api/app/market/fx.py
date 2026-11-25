"""Base-currency conversion (Mission 5 §24).

Converts instrument-currency values to a portfolio base currency using
verified FRED daily FX observations. The rate applied at date D is the
latest stored FX observation ON OR BEFORE D — never a future rate. When
no rate exists at or before D (or no conversion path exists), the result
is unavailable, never guessed.

Conventions (from the verified registry):
- "USD per EUR" (DEXUSEU): USD = amount_EUR * rate
- "CHF per USD" (DEXSZUS): CHF = amount_USD * rate
Every conversion goes through USD legs, so mult_to_usd(ccy) is the single
primitive: USD-value of 1 unit of ccy.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MarketInstrument, MarketObservation

BASE_CURRENCIES = ("CHF", "USD", "EUR", "GBP")
SUPPORTED_CURRENCIES = BASE_CURRENCIES + ("JPY", "CNY", "INR")

# instrument code -> (numerator_ccy, denominator_ccy): rate = numerator per denominator
_FX_SPECS = {
    "FX_USD_EUR": ("USD", "EUR"),
    "FX_USD_GBP": ("USD", "GBP"),
    "FX_CHF_USD": ("CHF", "USD"),
    "FX_JPY_USD": ("JPY", "USD"),
    "FX_CNY_USD": ("CNY", "USD"),
    "FX_INR_USD": ("INR", "USD"),
}


async def _rate_on_or_before(
    session: AsyncSession, fx_code: str, as_of: date
) -> tuple[date, float] | None:
    row = (
        await session.execute(
            select(
                MarketObservation.obs_date, MarketObservation.value
            )
            .join(
                MarketInstrument,
                MarketInstrument.id == MarketObservation.instrument_id,
            )
            .where(
                MarketInstrument.code == fx_code,
                MarketObservation.obs_date <= as_of,
            )
            .order_by(MarketObservation.obs_date.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    return row[0], row[1]


async def _mult_to_usd(
    session: AsyncSession, ccy: str, as_of: date
) -> tuple[float, dict] | None:
    """USD value of 1 unit of `ccy`, plus the leg used (or None)."""
    if ccy == "USD":
        return 1.0, {"instrument": "USD", "rate": 1.0, "rate_date": None,
                     "convention": "identity"}
    for code, (num, den) in _FX_SPECS.items():
        if num == ccy and den == "USD":
            # rate = ccy per USD -> 1 ccy = 1/rate USD
            hit = await _rate_on_or_before(session, code, as_of)
            if hit is None:
                return None
            d, r = hit
            return 1.0 / r, {
                "instrument": code, "rate_date": d.isoformat(),
                "rate": r, "convention": f"{num} per {den}",
            }
        if num == "USD" and den == ccy:
            # rate = USD per ccy -> 1 ccy = rate USD
            hit = await _rate_on_or_before(session, code, as_of)
            if hit is None:
                return None
            d, r = hit
            return r, {
                "instrument": code, "rate_date": d.isoformat(),
                "rate": r, "convention": f"{num} per {den}",
            }
    return None


async def convert(
    session: AsyncSession,
    amount: float,
    from_ccy: str,
    to_ccy: str,
    as_of: date,
) -> dict:
    """amount in from_ccy -> to_ccy at ≤as_of rates, via USD legs.

    Returns converted value plus the FX rates actually used (dates +
    staleness is the caller's transparency data). value=None with a
    reason when a required rate is missing — never a guessed rate.
    """
    if from_ccy == to_ccy:
        return {"value": amount, "from": from_ccy, "to": to_ccy,
                "as_of": as_of.isoformat(), "fx_used": []}
    if from_ccy not in SUPPORTED_CURRENCIES or to_ccy not in SUPPORTED_CURRENCIES:
        return {"value": None,
                "unavailable_reason": f"no conversion path {from_ccy}->{to_ccy}",
                "fx_used": []}

    fx_used: list[dict] = []
    mf = await _mult_to_usd(session, from_ccy, as_of)
    if mf is None:
        return {"value": None, "fx_used": fx_used,
                "unavailable_reason": f"no {from_ccy}/USD rate on or before {as_of}"}
    if mf[1]["instrument"] != "USD":
        fx_used.append(mf[1])
    mt = await _mult_to_usd(session, to_ccy, as_of)
    if mt is None:
        return {"value": None, "fx_used": fx_used,
                "unavailable_reason": f"no USD/{to_ccy} rate on or before {as_of}"}
    if mt[1]["instrument"] != "USD":
        fx_used.append(mt[1])
    return {
        "value": amount * mf[0] / mt[0],
        "from": from_ccy, "to": to_ccy, "as_of": as_of.isoformat(),
        "fx_used": fx_used,
    }
