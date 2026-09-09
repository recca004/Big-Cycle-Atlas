from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.config import get_settings
from app.db.session import get_session
from app.models import DataSource, Indicator
from app.schemas import CountryRead
from app.schemas import Observation as ObservationSchema
from app.schemas.force_coverage import ForceCoverageResponse, ForceCoverageRead, ForceInputRead
from app.schemas.pagination import PaginatedResponse
from app.services import country_service, force_coverage_service, observation_service


router = APIRouter(prefix=f"{get_settings().api_prefix}/countries", tags=["countries"])


def _parse_period_bound(value: str, *, is_end: bool) -> datetime:
    """'YYYY' or 'YYYY-MM-DD' → UTC datetime. End bounds are exclusive."""
    try:
        if len(value) == 4 and value.isdigit():
            d = date(int(value), 1, 1)
            if is_end:
                return datetime(d.year + 1, 1, 1, tzinfo=timezone.utc)
            return datetime(d.year, 1, 1, tzinfo=timezone.utc)
        d = date.fromisoformat(value)
        if is_end:
            return datetime(d.year, d.month, d.day, tzinfo=timezone.utc) + timedelta(days=1)
        return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Period bounds must be 'YYYY' or 'YYYY-MM-DD'",
        )


@router.get("", response_model=list[CountryRead])
async def list_countries(session: AsyncSession = Depends(get_session)):
    return await country_service.list_countries_with_coverage(session)


@router.get("/{iso3}", response_model=CountryRead)
async def get_country(iso3: str, session: AsyncSession = Depends(get_session)):
    country = await country_service.get_country(session, iso3)
    if country is None:
        raise HTTPException(
            status_code=404,
            detail=f"Country with ISO3 '{iso3}' not found",
        )
    return country


@router.get("/{iso3}/observations", response_model=PaginatedResponse[ObservationSchema])
async def list_country_observations(
    iso3: str,
    session: AsyncSession = Depends(get_session),
    indicator: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    country = await country_service.get_country(session, iso3)
    if country is None:
        raise HTTPException(
            status_code=404,
            detail=f"Country with ISO3 '{iso3}' not found",
        )

    indicator_id = None
    if indicator:
        indicator_id = (
            await session.execute(
                select(Indicator.id).where(Indicator.code == indicator.upper())
            )
        ).scalar_one_or_none()
        if indicator_id is None:
            raise HTTPException(
                status_code=404,
                detail=f"Indicator '{indicator}' not found",
            )

    data_source_id = None
    if source:
        data_source_id = (
            await session.execute(
                select(DataSource.id).where(DataSource.key == source)
            )
        ).scalar_one_or_none()
        if data_source_id is None:
            raise HTTPException(
                status_code=404,
                detail=f"Data source '{source}' not found",
            )

    period_from = _parse_period_bound(start, is_end=False) if start else None
    period_to = _parse_period_bound(end, is_end=True) if end else None

    observations, total_count = await observation_service.list_current_observations(
        session,
        country.id,
        indicator_id=indicator_id,
        data_source_id=data_source_id,
        period_start_from=period_from,
        period_start_to=period_to,
        limit=limit,
        offset=offset,
    )

    indicator_codes = dict(
        (await session.execute(select(Indicator.id, Indicator.code))).all()
    )
    source_keys = dict(
        (await session.execute(select(DataSource.id, DataSource.key))).all()
    )

    items = []
    for obs in observations:
        item = ObservationSchema.model_validate(obs)
        if obs.indicator_id in indicator_codes:
            item.indicator_code = indicator_codes[obs.indicator_id]
        if obs.data_source_id in source_keys:
            item.source_key = source_keys[obs.data_source_id]
        items.append(item)

    return PaginatedResponse(items=items, count=total_count, limit=limit, offset=offset)


@router.get("/{iso3}/force-coverage", response_model=ForceCoverageResponse)
async def get_country_force_coverage(
    iso3: str,
    session: AsyncSession = Depends(get_session),
):
    """Data coverage for the 17 Big Cycle forces — statuses only, never scores."""
    country = await country_service.get_country(session, iso3)
    if country is None:
        raise HTTPException(
            status_code=404,
            detail=f"Country with ISO3 '{iso3}' not found",
        )

    coverage = await force_coverage_service.get_force_coverage(session, country.id)

    forces = [
        ForceCoverageRead(
            code=item.definition.code,
            name=item.definition.name,
            description=item.definition.description,
            status=item.status,
            coverage_notes=item.definition.coverage_notes,
            live_inputs=[
                ForceInputRead(
                    indicator_code=i.indicator_code,
                    name=i.name,
                    has_data=i.has_data,
                    has_source_series=i.has_source_series,
                    source=i.source,
                    latest_period=i.latest_period,
                )
                for i in item.live_inputs
            ],
            candidate_inputs=[
                ForceInputRead(
                    indicator_code=i.indicator_code,
                    name=i.name,
                    has_data=i.has_data,
                    has_source_series=i.has_source_series,
                    source=i.source,
                    latest_period=i.latest_period,
                )
                for i in item.candidate_inputs
            ],
        )
        for item in coverage
    ]
    return ForceCoverageResponse(country=country.iso3, forces=forces)
