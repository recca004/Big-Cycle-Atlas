from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.config import get_settings
from app.cycle.force_definitions import FORCE_DEFINITIONS
from app.cycle.normalization_definitions import CURRENT_MODEL_VERSION, ScoringPeriod
from app.db.session import get_session
from app.models import DataSource, Indicator
from app.schemas import CountryRead
from app.schemas import Observation as ObservationSchema
from app.schemas.force_coverage import ForceCoverageResponse, ForceCoverageRead, ForceInputRead
from app.schemas.force_scores import (
    CountryUncertaintyResponse,
    ForceHistoryPoint,
    ForceHistoryResponse,
    UncertaintyIndicatorRead,
)
from app.schemas.force_scores import ForceScoreRead, ForceScoresResponse
from app.schemas.pagination import PaginatedResponse
from app.services import country_service, force_coverage_service, force_signal_service, observation_service
from app.services.alignment_service import AlignmentError, parse_scoring_period


router = APIRouter(prefix=f"{get_settings().api_prefix}/countries", tags=["countries"])


def _latest_completed_scoring_period() -> ScoringPeriod:
    """The most recent quarter that has fully ended (release-date discipline)."""
    today = datetime.now(timezone.utc).date()
    quarter = (today.month - 1) // 3 + 1
    if quarter == 1:
        return ScoringPeriod(today.year - 1, 4)
    return ScoringPeriod(today.year, quarter - 1)


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


_FORCE_NAMES = {d.code: d.name for d in FORCE_DEFINITIONS}


@router.get("/{iso3}/force-scores", response_model=ForceScoresResponse)
async def get_country_force_scores(
    iso3: str,
    period: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Derived force-level scores — read-only, never persisted.

    Returns all 17 forces. Unscored forces report level/relative/momentum as
    null with execution_status "deferred" — missing data is never a zero.
    """
    country = await country_service.get_country(session, iso3)
    if country is None:
        raise HTTPException(
            status_code=404,
            detail=f"Country with ISO3 '{iso3}' not found",
        )

    if period is None:
        scoring_period = _latest_completed_scoring_period()
    else:
        try:
            scoring_period = parse_scoring_period(period)
        except AlignmentError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    signals = await force_signal_service.build_force_signals_as_of(
        session, country.iso3, scoring_period
    )

    forces = [
        ForceScoreRead(
            force_code=s.force_code,
            force_name=_FORCE_NAMES.get(s.force_code, s.force_code),
            execution_status=(
                "scored" if s.level_score is not None
                else "dimension_only"
                if (s.relative_score is not None or s.momentum is not None)
                else "deferred"
            ),
            level_score=s.level_score,
            relative_score=s.relative_score,
            momentum_score=s.momentum,
            confidence=s.confidence,
            coverage_status=s.coverage_status.value,
            period=s.scoring_period,
            model_version=s.force_model_version,
            limitations=[
                *(
                    [f"missing components: {', '.join(s.missing_components)}"]
                    if s.missing_components
                    else []
                ),
                *(
                    [
                        "deferred components: "
                        + ", ".join(s.deferred_components)
                    ]
                    if s.deferred_components
                    else []
                ),
            ],
            reasons=[
                *(
                    ["component observation missing or too stale"]
                    if s.missing_components
                    else []
                ),
                *(
                    ["component normalization deferred (supporting context)"]
                    if s.deferred_components
                    else []
                ),
                *(
                    ["force aggregation approved (identity copy)"]
                    if s.aggregation_method.value == "identity_single"
                    and s.level_score is not None
                    else ["force aggregation deferred — no numeric composition approved"]
                ),
            ],
            backtest_safe=s.backtest_safe,
        )
        for s in signals
    ]

    return ForceScoresResponse(
        country=country.iso3,
        normalization_version=signals[0].normalization_model_version
        if signals
        else "",
        force_aggregation_version=signals[0].force_model_version if signals else "",
        forces=forces,
    )


@router.get("/{iso3}/forces/{force_code}/history", response_model=ForceHistoryResponse)
async def get_country_force_history(
    iso3: str,
    force_code: str,
    start_year: int = Query(1990, ge=1960, le=2200),
    end_year: Optional[int] = Query(None, ge=1960, le=2200),
    session: AsyncSession = Depends(get_session),
):
    """Retrospective force history at annual (Q4) scoring snapshots.

    RETROSPECTIVE — each point uses latest stored vintages; not a
    release-date-safe backtest (backtest_safe=False). Missing inputs at a
    period produce nulls, never zeros.
    """
    country = await country_service.get_country(session, iso3)
    if country is None:
        raise HTTPException(
            status_code=404,
            detail=f"Country with ISO3 '{iso3}' not found",
        )
    if force_code not in _FORCE_NAMES:
        raise HTTPException(
            status_code=404, detail=f"Unknown force code '{force_code}'"
        )
    if end_year is None:
        end_year = _latest_completed_scoring_period().year
    if end_year < start_year:
        raise HTTPException(status_code=422, detail="end_year < start_year")

    latest = _latest_completed_scoring_period()
    points: list[ForceHistoryPoint] = []
    for year in range(start_year, end_year + 1):
        scoring_period = ScoringPeriod(year, 4)
        if (scoring_period.year, scoring_period.quarter) > (latest.year, latest.quarter):
            break  # never score a future snapshot
        signals = await force_signal_service.build_force_signals_as_of(
            session, country.iso3, scoring_period
        )
        s = next(f for f in signals if f.force_code == force_code)
        points.append(
            ForceHistoryPoint(
                period=s.scoring_period,
                execution_status=(
                    "scored" if s.level_score is not None
                    else "dimension_only"
                    if (s.relative_score is not None or s.momentum is not None)
                    else "deferred"
                ),
                level_score=s.level_score,
                relative_score=s.relative_score,
                momentum_score=s.momentum,
                coverage_status=s.coverage_status.value,
                missing_components=list(s.missing_components),
            )
        )
    return ForceHistoryResponse(
        country=country.iso3,
        force_code=force_code,
        force_name=_FORCE_NAMES[force_code],
        model_version=CURRENT_MODEL_VERSION.version_id,
        points=points,
    )


@router.get("/{iso3}/uncertainty", response_model=CountryUncertaintyResponse)
async def get_country_uncertainty(
    iso3: str,
    session: AsyncSession = Depends(get_session),
):
    """Published provider uncertainty diagnostics (DEC-022/023 contract).

    Returns each indicator's LATEST available period's published bounds and
    source counts. Only provider-published values are returned — no
    computed confidence percentage exists anywhere in this contract.
    """
    from sqlalchemy import func as sa_func, select as sa_select

    from app.models.indicator import Indicator
    from app.models.indicator_diagnostic import (
        IndicatorDiagnostic,
        IndicatorDiagnosticKind,
    )

    country = await country_service.get_country(session, iso3)
    if country is None:
        raise HTTPException(
            status_code=404,
            detail=f"Country with ISO3 '{iso3}' not found",
        )

    # Latest period per (indicator, kind), then the latest vintage at it.
    latest_period = (
        sa_select(
            IndicatorDiagnostic.indicator_id,
            IndicatorDiagnostic.diagnostic_kind,
            sa_func.max(IndicatorDiagnostic.period_start).label("max_period"),
        )
        .where(IndicatorDiagnostic.country_id == country.id)
        .group_by(
            IndicatorDiagnostic.indicator_id, IndicatorDiagnostic.diagnostic_kind
        )
        .subquery()
    )
    latest_vintage = (
        sa_select(
            IndicatorDiagnostic.indicator_id,
            IndicatorDiagnostic.diagnostic_kind,
            IndicatorDiagnostic.period_start,
            sa_func.max(IndicatorDiagnostic.vintage_number).label("max_v"),
        )
        .join(
            latest_period,
            (IndicatorDiagnostic.indicator_id == latest_period.c.indicator_id)
            & (
                IndicatorDiagnostic.diagnostic_kind
                == latest_period.c.diagnostic_kind
            )
            & (IndicatorDiagnostic.period_start == latest_period.c.max_period),
        )
        .where(IndicatorDiagnostic.country_id == country.id)
        .group_by(
            IndicatorDiagnostic.indicator_id,
            IndicatorDiagnostic.diagnostic_kind,
            IndicatorDiagnostic.period_start,
        )
        .subquery()
    )
    rows = (
        await session.execute(
            sa_select(
                Indicator.code,
                IndicatorDiagnostic.diagnostic_kind,
                IndicatorDiagnostic.period_start,
                IndicatorDiagnostic.value,
            )
            .join(
                latest_vintage,
                (IndicatorDiagnostic.indicator_id == latest_vintage.c.indicator_id)
                & (
                    IndicatorDiagnostic.diagnostic_kind
                    == latest_vintage.c.diagnostic_kind
                )
                & (IndicatorDiagnostic.period_start == latest_vintage.c.period_start)
                & (
                    IndicatorDiagnostic.vintage_number == latest_vintage.c.max_v
                ),
            )
            .join(Indicator, Indicator.id == IndicatorDiagnostic.indicator_id)
            .where(IndicatorDiagnostic.country_id == country.id)
        )
    ).all()

    by_indicator: dict[str, dict] = {}
    for code, kind, period_start, value in rows:
        entry = by_indicator.setdefault(
            code, {"source_period": period_start.date().isoformat()}
        )
        entry[kind if isinstance(kind, str) else kind.value] = value

    return CountryUncertaintyResponse(
        country=country.iso3,
        indicators=[
            UncertaintyIndicatorRead(indicator_code=code, **entry)
            for code, entry in sorted(by_indicator.items())
        ],
    )
