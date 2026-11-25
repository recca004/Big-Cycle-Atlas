"""Experimental market regime API (Mission 5 §22, §25, §39)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.research import regime_service
from app.research.regime import REGIME_ENGINE_VERSION

router = APIRouter(prefix=f"{get_settings().api_prefix}/regimes", tags=["regimes"])


@router.get("/model")
async def regime_model_info():
    return {
        "engine_version": REGIME_ENGINE_VERSION,
        "model_id": "market_regime_growth_inflation_v1",
        "methodology_status": "experimental",
        "framework": "growth x inflation directions, annual cadence",
        "categories": [
            "REFLATION (improving growth + rising inflation)",
            "GOLDILOCKS (improving growth + falling inflation)",
            "STAGFLATION (weakening growth + rising inflation)",
            "DISINFLATION_SLOWDOWN (weakening + falling)",
            "UNCLASSIFIED (insufficient inputs)",
        ],
        "separate_measurements": [
            "policy_rate", "long_yield", "real_rate_proxy",
            "currency_return",
        ],
        "disclaimer": (
            "Regime labels are research categories, not market laws; "
            "retrospective only — never an actionable signal."
        ),
    }


@router.get("/countries/{iso3}/history")
async def country_regime_history(
    iso3: str, session: AsyncSession = Depends(get_session)
):
    hist = await regime_service.regime_history(session, iso3.upper())
    if hist is None:
        raise HTTPException(404, f"Country {iso3!r} not found")
    return hist


@router.get("/countries/{iso3}/asset-returns")
async def country_regime_asset_returns(
    iso3: str, session: AsyncSession = Depends(get_session)
):
    res = await regime_service.regime_asset_returns(session, iso3.upper())
    if res is None:
        raise HTTPException(404, f"Country {iso3!r} not found")
    return res
