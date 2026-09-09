from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Country, Observation, SourceSeries
from app.schemas import CountryRead


async def list_countries(session: AsyncSession) -> list[Country]:
    result = await session.execute(select(Country).order_by(Country.name))
    return list(result.scalars().all())


async def list_countries_with_coverage(session: AsyncSession) -> list[CountryRead]:
    """Countries plus latest-vintage data coverage, in one aggregate query.

    Coverage counts only current observations (max vintage per country /
    source series / period), so superseded vintages don't inflate the numbers.
    """
    countries = (await session.execute(select(Country).order_by(Country.name))).scalars().all()

    latest_vintage = (
        select(
            Observation.country_id,
            Observation.source_series_id,
            Observation.period_start,
            func.max(Observation.vintage_number).label("max_vintage"),
        )
        .group_by(Observation.country_id, Observation.source_series_id, Observation.period_start)
        .subquery()
    )

    rows = (
        await session.execute(
            select(
                Observation.country_id,
                func.count().label("observation_count"),
                func.count(func.distinct(SourceSeries.indicator_id)).label("indicator_count"),
                func.max(func.extract("year", Observation.period_start)).label("latest_year"),
            )
            .join(
                latest_vintage,
                and_(
                    Observation.country_id == latest_vintage.c.country_id,
                    Observation.source_series_id == latest_vintage.c.source_series_id,
                    Observation.period_start == latest_vintage.c.period_start,
                    Observation.vintage_number == latest_vintage.c.max_vintage,
                ),
            )
            .join(SourceSeries, SourceSeries.id == Observation.source_series_id)
            .group_by(Observation.country_id)
        )
    ).all()

    coverage = {row.country_id: row for row in rows}

    items: list[CountryRead] = []
    for country in countries:
        schema = CountryRead.model_validate(country)
        cov = coverage.get(country.id)
        if cov is not None:
            schema.observation_count = cov.observation_count
            schema.indicator_count = cov.indicator_count
            schema.latest_observation_year = int(cov.latest_year)
        items.append(schema)
    return items


async def get_country(session: AsyncSession, iso3: str) -> Country | None:
    result = await session.execute(select(Country).where(Country.iso3 == iso3.upper()))
    return result.scalars().first()