"""Market research API (Mission 5 §23, §38).

Read-only endpoints over the market layer. Every response carries the
instrument's return_methodology — a yield is never displayed as a return.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.market import fx as fx_service
from app.market import service as market_service
from app.models import MarketInstrument, MarketObservation

router = APIRouter(prefix=f"{get_settings().api_prefix}/markets", tags=["markets"])


def _inst_json(i: MarketInstrument) -> dict:
    return {
        "code": i.code,
        "name": i.name,
        "asset_class": i.asset_class,
        "return_methodology": i.return_methodology,
        "country_id": i.country_id,
        "currency": i.currency,
        "unit": i.unit,
        "frequency": i.frequency,
        "external_code": i.external_code,
        "quote_convention": i.quote_convention,
        "notes": i.notes,
        "active": i.active,
    }


@router.get("/instruments")
async def list_instruments(
    asset_class: Optional[str] = None,
    currency: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    q = select(MarketInstrument).where(MarketInstrument.active).order_by(
        MarketInstrument.asset_class, MarketInstrument.code
    )
    if asset_class:
        q = q.where(MarketInstrument.asset_class == asset_class)
    if currency:
        q = q.where(MarketInstrument.currency == currency)
    rows = list((await session.execute(q)).scalars())
    return {
        "instruments": [_inst_json(i) for i in rows],
        "count": len(rows),
        "note": (
            "return_methodology describes what stored values ARE — "
            "yield_quote/spot_price/exchange_rate are NOT investment "
            "returns."
        ),
    }


@router.get("/coverage")
async def market_coverage(session: AsyncSession = Depends(get_session)):
    """Per-instrument observation counts and date ranges."""
    rows = (
        await session.execute(
            select(
                MarketInstrument.code,
                MarketInstrument.asset_class,
                MarketInstrument.frequency,
                func.count(MarketObservation.id),
                func.min(MarketObservation.obs_date),
                func.max(MarketObservation.obs_date),
                func.max(MarketObservation.retrieved_at),
            )
            .outerjoin(
                MarketObservation,
                MarketObservation.instrument_id == MarketInstrument.id,
            )
            .where(MarketInstrument.active)
            .group_by(
                MarketInstrument.code,
                MarketInstrument.asset_class,
                MarketInstrument.frequency,
            )
            .order_by(MarketInstrument.code)
        )
    ).all()
    return {
        "instruments": [
            {
                "code": code,
                "asset_class": ac,
                "frequency": fq,
                "observations": n,
                "earliest": e.isoformat() if e else None,
                "latest": l.isoformat() if l else None,
                "last_retrieved": r.isoformat() if r else None,
            }
            for code, ac, fq, n, e, l, r in rows
        ],
        "note": "Dates are provider observation dates; last_retrieved is "
                "Atlas first-observed evidence — not real-time pricing.",
    }


@router.get("/instruments/{code}/history")
async def instrument_history(
    code: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
    limit: int = Query(5000, le=20000),
    session: AsyncSession = Depends(get_session),
):
    hit = await market_service.instrument_history(
        session, code, start, end, limit
    )
    if hit is None:
        raise HTTPException(404, f"Unknown instrument {code!r}")
    inst, rows = hit
    return {
        "instrument": _inst_json(inst),
        "observations": [
            {"date": o.obs_date.isoformat(), "value": o.value}
            for o in rows
        ],
        "count": len(rows),
        "bounded": len(rows) == limit,
    }


@router.get("/instruments/{code}/returns")
async def instrument_returns(
    code: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
    session: AsyncSession = Depends(get_session),
):
    """Simple returns + performance stats on stored values (§23).

    The methodology label on each instrument governs interpretation:
    returns on a yield_quote are yield changes, NOT bond returns.
    """
    hit = await market_service.instrument_history(session, code, start, end)
    if hit is None:
        raise HTTPException(404, f"Unknown instrument {code!r}")
    inst, rows = hit
    obs = [(o.obs_date, o.value) for o in rows]
    ppy = 252 if inst.frequency == "daily" else 12
    rets = market_service.simple_returns(obs)
    stats = market_service.performance_stats(obs, periods_per_year=ppy)
    return {
        "instrument": _inst_json(inst),
        "calc_version": market_service.MARKET_CALC_VERSION,
        "return_methodology": inst.return_methodology,
        "returns": [
            {"date": d, "value": v} for d, v in rets.points
        ],
        "statistics": stats,
        "warning": (
            "Returns computed on stored values; dividends, roll and "
            "carry are NOT modelled — see return_methodology."
        ),
    }


@router.get("/instruments/{code}/rolling")
async def instrument_rolling(
    code: str,
    window: int = Query(60, ge=5, le=756),
    kind: str = Query("volatility", pattern="^(volatility|return)$"),
    start: Optional[date] = None,
    end: Optional[date] = None,
    session: AsyncSession = Depends(get_session),
):
    hit = await market_service.instrument_history(session, code, start, end)
    if hit is None:
        raise HTTPException(404, f"Unknown instrument {code!r}")
    inst, rows = hit
    obs = [(o.obs_date, o.value) for o in rows]
    ppy = 252 if inst.frequency == "daily" else 12
    return {
        "instrument": _inst_json(inst),
        "window": window,
        "kind": kind,
        "points": market_service.rolling_stat(
            obs, window, kind, periods_per_year=ppy
        ),
    }


@router.get("/correlations")
async def correlations(
    codes: str = Query(..., description="comma-separated instrument codes"),
    start: Optional[date] = None,
    end: Optional[date] = None,
    session: AsyncSession = Depends(get_session),
):
    """Pairwise return correlations on shared dates only (§23)."""
    code_list = [c.strip() for c in codes.split(",") if c.strip()]
    if not 2 <= len(code_list) <= 12:
        raise HTTPException(422, "2-12 instrument codes required")
    series = {}
    for c in code_list:
        hit = await market_service.instrument_history(session, c, start, end)
        if hit is None:
            raise HTTPException(404, f"Unknown instrument {c!r}")
        _, rows = hit
        series[c] = [(o.obs_date, o.value) for o in rows]
    return market_service.correlation_matrix(series)


@router.get("/fx/convert")
async def fx_convert(
    amount: float,
    from_ccy: str = Query(..., alias="from"),
    to: str = Query(...),
    as_of: Optional[date] = None,
    session: AsyncSession = Depends(get_session),
):
    """Convert an amount between supported currencies (§24).

    Uses the latest stored FX rate on or before as_of — never a future
    rate; value=null with a reason when a rate is missing."""
    result = await fx_service.convert(
        session, amount, from_ccy.upper(), to.upper(),
        as_of or date.today(),
    )
    return result
