from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_sources.base import ObservationDTO
from app.models.observation import Observation
from app.models.indicator_revision import IndicatorRevision
from app.models.country import Country
from app.models.data_source import DataSource
from app.models.indicator import Indicator
from app.models.source_series import SourceSeries


async def list_observations(
    session: AsyncSession,
    country_id: Optional[int] = None,
    indicator_id: Optional[int] = None,
    data_source_id: Optional[int] = None,
    source_series_id: Optional[int] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Observation], int]:
    query = select(Observation)
    if country_id:
        query = query.where(Observation.country_id == country_id)
    if indicator_id:
        query = query.where(Observation.indicator_id == indicator_id)
    if data_source_id:
        query = query.where(Observation.data_source_id == data_source_id)
    if source_series_id:
        query = query.where(Observation.source_series_id == source_series_id)
    if start:
        query = query.where(Observation.period_start >= start)
    if end:
        query = query.where(Observation.period_end <= end)

    # Pagination
    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    items = list(result.scalars().all())

    # Get total count for pagination
    count_query = select(func.count()).select_from(Observation)
    if country_id:
        count_query = count_query.where(Observation.country_id == country_id)
    if indicator_id:
        count_query = count_query.where(Observation.indicator_id == indicator_id)
    if data_source_id:
        count_query = count_query.where(Observation.data_source_id == data_source_id)
    if source_series_id:
        count_query = count_query.where(Observation.source_series_id == source_series_id)
    if start:
        count_query = count_query.where(Observation.period_start >= start)
    if end:
        count_query = count_query.where(Observation.period_end <= end)

    count_result = await session.execute(count_query)
    total_count = count_result.scalar_one()

    return items, total_count


async def list_current_observations(
    session: AsyncSession,
    country_id: int,
    indicator_id: Optional[int] = None,
    data_source_id: Optional[int] = None,
    period_start_from: Optional[datetime] = None,
    period_start_to: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Observation], int]:
    """Latest-vintage observations for one country (one row per series+period).

    Older vintages stay in the DB but are excluded here so the normal country
    data view never presents superseded values as current. Historical access
    can come later via a dedicated revisions endpoint.

    Every filter (source, indicator, period bounds) is applied to the
    latest-vintage subquery, the outer query and the count query — SourceSeries
    rows are shared across countries, so scoping only one scope leaks rows
    (ISSUE-004).
    """
    subquery = (
        select(
            Observation.source_series_id,
            Observation.period_start,
            func.max(Observation.vintage_number).label("max_vintage"),
        )
        .where(Observation.country_id == country_id)
        .group_by(Observation.source_series_id, Observation.period_start)
    )
    if indicator_id:
        subquery = subquery.where(Observation.indicator_id == indicator_id)
    if data_source_id:
        subquery = subquery.where(Observation.data_source_id == data_source_id)
    if period_start_from:
        subquery = subquery.where(Observation.period_start >= period_start_from)
    if period_start_to:
        subquery = subquery.where(Observation.period_start < period_start_to)
    subquery = subquery.subquery()

    query = (
        select(Observation)
        .where(Observation.country_id == country_id)
        .join(
            subquery,
            (Observation.source_series_id == subquery.c.source_series_id)
            & (Observation.period_start == subquery.c.period_start)
            & (Observation.vintage_number == subquery.c.max_vintage),
        )
        .order_by(Observation.period_start.desc())
    )
    if indicator_id:
        query = query.where(Observation.indicator_id == indicator_id)
    if data_source_id:
        query = query.where(Observation.data_source_id == data_source_id)
    if period_start_from:
        query = query.where(Observation.period_start >= period_start_from)
    if period_start_to:
        query = query.where(Observation.period_start < period_start_to)

    result = await session.execute(query.offset(offset).limit(limit))
    items = list(result.scalars().all())

    count_query = (
        select(func.count())
        .select_from(Observation)
        .where(Observation.country_id == country_id)
        .join(
            subquery,
            (Observation.source_series_id == subquery.c.source_series_id)
            & (Observation.period_start == subquery.c.period_start)
            & (Observation.vintage_number == subquery.c.max_vintage),
        )
    )
    if indicator_id:
        count_query = count_query.where(Observation.indicator_id == indicator_id)
    if data_source_id:
        count_query = count_query.where(Observation.data_source_id == data_source_id)
    if period_start_from:
        count_query = count_query.where(Observation.period_start >= period_start_from)
    if period_start_to:
        count_query = count_query.where(Observation.period_start < period_start_to)
    total_count = (await session.execute(count_query)).scalar_one()

    return items, total_count


class ObservationPersistenceError(Exception):
    """An ObservationDTO could not be resolved to a consistent DB identity.

    Raised instead of persisting ambiguous data — e.g. unknown country, unknown
    source, unmapped indicator, or a SourceSeries pointing at a different
    canonical indicator than the DTO claims.
    """


@dataclass
class PersistenceResult:
    received: int
    inserted: int
    skipped: int
    revised: int


def _as_utc(dt: date | datetime) -> datetime:
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.combine(dt, time.min, tzinfo=timezone.utc)


async def persist_observations(
    session: AsyncSession, dtos: list[ObservationDTO]
) -> PersistenceResult:
    """Resolve DTO identities and persist valid observations.

    Idempotent: compared against the latest vintage for (country, source
    series, period) — same value → skipped; different value → a new vintage
    Observation is inserted (superseding the latest, never overwriting it)
    plus an IndicatorRevision row, so history stays fully queryable.

    Uses add/flush only — commit ownership stays with the caller.
    """
    result = PersistenceResult(received=len(dtos), inserted=0, skipped=0, revised=0)

    countries: dict[str, Country] = {}
    sources: dict[str, DataSource] = {}
    indicators: dict[str, Indicator] = {}
    series: dict[tuple[int, str], SourceSeries] = {}

    async def _country(iso3: str) -> Country:
        if iso3 not in countries:
            row = (
                await session.execute(select(Country).where(Country.iso3 == iso3))
            ).scalar_one_or_none()
            if row is None:
                raise ObservationPersistenceError(
                    f"Unknown country iso3: {iso3!r}"
                )
            countries[iso3] = row
        return countries[iso3]

    async def _source(key: str) -> DataSource:
        if key not in sources:
            row = (
                await session.execute(select(DataSource).where(DataSource.key == key))
            ).scalar_one_or_none()
            if row is None:
                raise ObservationPersistenceError(
                    f"Unknown data source key: {key!r}"
                )
            sources[key] = row
        return sources[key]

    async def _indicator(code: str) -> Indicator:
        if code not in indicators:
            row = (
                await session.execute(select(Indicator).where(Indicator.code == code))
            ).scalar_one_or_none()
            if row is None:
                raise ObservationPersistenceError(
                    f"Unknown indicator code: {code!r}"
                )
            indicators[code] = row
        return indicators[code]

    async def _series(data_source_id: int, external_code: str) -> SourceSeries:
        cache_key = (data_source_id, external_code)
        if cache_key not in series:
            row = (
                await session.execute(
                    select(SourceSeries).where(
                        SourceSeries.data_source_id == data_source_id,
                        SourceSeries.external_code == external_code,
                    )
                )
            ).scalar_one_or_none()
            if row is None:
                raise ObservationPersistenceError(
                    f"No SourceSeries for external code {external_code!r} "
                    f"on data source id {data_source_id}"
                )
            series[cache_key] = row
        return series[cache_key]

    for dto in dtos:
        country = await _country(dto.country_iso3)
        source = await _source(dto.source_key)
        indicator = await _indicator(dto.indicator_code)
        source_series = await _series(source.id, dto.external_series_code)

        if source_series.indicator_id != indicator.id:
            raise ObservationPersistenceError(
                f"SourceSeries {source_series.external_code!r} points to indicator "
                f"id {source_series.indicator_id}, but DTO claims indicator "
                f"{dto.indicator_code!r} (id {indicator.id})"
            )

        period_start = _as_utc(dto.observation_date)
        latest = (
            await session.execute(
                select(Observation)
                .where(
                    Observation.country_id == country.id,
                    Observation.source_series_id == source_series.id,
                    Observation.period_start == period_start,
                )
                .order_by(Observation.vintage_number.desc(), Observation.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

        if latest is not None and latest.value == dto.value:
            result.skipped += 1
            continue

        if latest is not None:
            new_observation = Observation(
                country_id=country.id,
                indicator_id=indicator.id,
                data_source_id=source.id,
                source_series_id=source_series.id,
                period_start=period_start,
                period_end=None,
                value=dto.value,
                unit=dto.unit,
                observation_date=_as_utc(dto.observation_date),
                release_date=dto.release_date,
                retrieved_at=_as_utc(dto.retrieved_at),
                vintage_number=latest.vintage_number + 1,
                supersedes_observation_id=latest.id,
                raw_payload=dto.raw_payload,
            )
            session.add(new_observation)
            await session.flush()
            session.add(
                IndicatorRevision(
                    prior_observation_id=latest.id,
                    new_observation_id=new_observation.id,
                    old_value=latest.value,
                    new_value=dto.value,
                    delta=dto.value - latest.value,
                )
            )
            result.revised += 1
            continue

        session.add(
            Observation(
                country_id=country.id,
                indicator_id=indicator.id,
                data_source_id=source.id,
                source_series_id=source_series.id,
                period_start=period_start,
                period_end=None,
                value=dto.value,
                unit=dto.unit,
                observation_date=_as_utc(dto.observation_date),
                release_date=dto.release_date,
                retrieved_at=_as_utc(dto.retrieved_at),
                raw_payload=dto.raw_payload,
            )
        )
        result.inserted += 1

    await session.flush()
    return result
