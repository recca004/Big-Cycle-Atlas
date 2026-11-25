from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import Country, DataSource, Indicator, Observation, SourceSeries
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
    start_year: int = Query(1980, ge=1960, le=2200),
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


@router.get("/series")
async def observatory_series(
    indicator: str = Query("GDP_CURRENT_USD"),
    start_year: int = Query(1970, ge=1800, le=2200),
    session: AsyncSession = Depends(get_session),
):
    """Latest-vintage measure history across all tracked countries."""
    latest_vintage = (
        select(
            Observation.country_id.label("country_id"),
            Observation.source_series_id.label("source_series_id"),
            Observation.period_start.label("period_start"),
            func.max(Observation.vintage_number).label("vintage"),
        )
        .group_by(
            Observation.country_id,
            Observation.source_series_id,
            Observation.period_start,
        )
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                Country.iso3,
                Indicator.name,
                Indicator.unit,
                Observation.period_start,
                Observation.value,
                Observation.vintage_number,
                DataSource.name.label("source"),
            )
            .select_from(Observation)
            .join(Country, Country.id == Observation.country_id)
            .join(Indicator, Indicator.id == Observation.indicator_id)
            .join(DataSource, DataSource.id == Observation.data_source_id)
            .join(
                latest_vintage,
                (Observation.country_id == latest_vintage.c.country_id)
                & (Observation.source_series_id == latest_vintage.c.source_series_id)
                & (Observation.period_start == latest_vintage.c.period_start)
                & (Observation.vintage_number == latest_vintage.c.vintage),
            )
            .where(Indicator.code == indicator)
            .where(func.extract("year", Observation.period_start) >= start_year)
            .order_by(Country.iso3, Observation.period_start)
        )
    ).all()
    countries: dict[str, dict] = {}
    for iso3, name, unit, period, value, vintage, source in rows:
        entry = countries.setdefault(
            iso3,
            {
                "iso3": iso3,
                "indicator_name": name,
                "unit": unit,
                "source": source,
                "points": [],
            },
        )
        entry["points"].append(
            {
                "period": period.year,
                "value": value,
                "vintage": vintage,
            }
        )
    return {
        "indicator": indicator,
        "start_year": start_year,
        "countries": list(countries.values()),
    }


@router.get("/coverage")
async def observatory_coverage(
    session: AsyncSession = Depends(get_session),
):
    """Bounded raw-observation coverage for the eight tracked countries."""
    rows = (
        await session.execute(
            select(
                Country.iso3,
                Country.name,
                Indicator.code,
                Indicator.name,
                Indicator.unit,
                Indicator.frequency,
                DataSource.key,
                func.min(Observation.period_start).label("earliest"),
                func.max(Observation.period_start).label("latest"),
                func.count(func.distinct(Observation.period_start)).label(
                    "period_count"
                ),
            )
            .select_from(Observation)
            .join(Country, Country.id == Observation.country_id)
            .join(Indicator, Indicator.id == Observation.indicator_id)
            .join(SourceSeries, SourceSeries.id == Observation.source_series_id)
            .join(DataSource, DataSource.id == Observation.data_source_id)
            .group_by(
                Country.iso3,
                Country.name,
                Indicator.code,
                Indicator.name,
                Indicator.unit,
                Indicator.frequency,
                DataSource.key,
            )
            .order_by(Country.iso3, Indicator.code, DataSource.key)
        )
    ).all()
    return {
        "coverage_kind": "raw_observations_all_vintages",
        "countries": 8,
        "series": [
            {
                "country": iso3,
                "country_name": name,
                "indicator": code,
                "indicator_name": indicator_name,
                "unit": unit,
                "frequency": frequency,
                "source": source,
                "earliest_period": earliest.date().isoformat() if earliest else None,
                "latest_period": latest.date().isoformat() if latest else None,
                "periods": int(period_count),
            }
            for (
                iso3,
                name,
                code,
                indicator_name,
                unit,
                frequency,
                source,
                earliest,
                latest,
                period_count,
            ) in rows
        ],
    }


@router.get("/transition")
async def observatory_transition(
    incumbent: str = Query("USA"),
    challenger: str = Query("CHN"),
    model: str = Query("model_b_domain"),
    start_year: int = Query(1980, ge=1960, le=2200),
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
