from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import Observation
from app.research import observatory as observatory_service
from app.research.composite import COMPOSITE_MODELS

router = APIRouter(prefix="/api/observatory", tags=["observatory"])


class RefreshRequest(BaseModel):
    model: str = "model_b_domain"
    collect_providers: bool = False
    sources: Optional[list[str]] = None


async def _strict_count(session: AsyncSession) -> int:
    return int(
        (
            await session.execute(
                select(func.count(Observation.id)).where(
                    Observation.retrieved_at.isnot(None)
                )
            )
        ).scalar()
        or 0
    )


@router.get("/overview")
async def observatory_overview(
    model: str = Query("model_b_domain"),
    incumbent: str = Query("USA"),
    challenger: str = Query("CHN"),
    start_year: int = Query(2000, ge=1990, le=2200),
    session: AsyncSession = Depends(get_session),
):
    if model not in COMPOSITE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown model {model!r}")
    core = await observatory_service.compute_core_observatory(
        session, model_id=model, start_year=start_year
    )
    strict_cnt = await _strict_count(session)
    transition = observatory_service.build_transition_monitor(
        core,
        incumbent_iso3=incumbent,
        challenger_iso3=challenger,
        strict_eligible_periods=strict_cnt,
    )
    freshness, daily_changes = (
        await observatory_service.build_freshness_and_changes(session, core)
    )
    return {
        "methodology_status": core["methodology_status"],
        "normalization_version": core["normalization_version"],
        "model": core["model"],
        "scoring_period": core["scoring_period"],
        "available_periods": core["available_periods"],
        "countries": core["countries"],
        "power_summary": core["power_summary"],
        "transition_monitor": transition,
        "freshness": freshness,
        "daily_changes": daily_changes,
        "refresh_job": observatory_service.get_refresh_job_status(),
    }


@router.get("/transition")
async def observatory_transition(
    incumbent: str = Query("USA"),
    challenger: str = Query("CHN"),
    model: str = Query("model_b_domain"),
    start_year: int = Query(2000, ge=1990, le=2200),
    session: AsyncSession = Depends(get_session),
):
    if model not in COMPOSITE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown model {model!r}")
    core = await observatory_service.compute_core_observatory(
        session, model_id=model, start_year=start_year
    )
    strict_cnt = await _strict_count(session)
    return observatory_service.build_transition_monitor(
        core,
        incumbent_iso3=incumbent,
        challenger_iso3=challenger,
        strict_eligible_periods=strict_cnt,
    )


@router.get("/freshness")
async def observatory_freshness(
    model: str = Query("model_b_domain"),
    session: AsyncSession = Depends(get_session),
):
    if model not in COMPOSITE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown model {model!r}")
    core = await observatory_service.compute_core_observatory(
        session, model_id=model
    )
    freshness, _ = await observatory_service.build_freshness_and_changes(
        session, core
    )
    return freshness


@router.get("/changes")
async def observatory_changes(
    model: str = Query("model_b_domain"),
    session: AsyncSession = Depends(get_session),
):
    if model not in COMPOSITE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown model {model!r}")
    core = await observatory_service.compute_core_observatory(
        session, model_id=model
    )
    _, daily_changes = await observatory_service.build_freshness_and_changes(
        session, core
    )
    return daily_changes


@router.get("/refresh/status")
async def observatory_refresh_status():
    return observatory_service.get_refresh_job_status()


@router.post("/refresh")
async def observatory_refresh(
    body: RefreshRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    req = body or RefreshRequest()
    if req.model not in COMPOSITE_MODELS:
        raise HTTPException(
            status_code=422, detail=f"Unknown model {req.model!r}"
        )
    accepted, payload = await observatory_service.trigger_refresh_job(
        session,
        model_id=req.model,
        collect_providers=req.collect_providers,
        sources=req.sources,
    )
    if not accepted:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "An observatory refresh or collection job is already running.",
                "job": payload,
            },
        )
    return payload
