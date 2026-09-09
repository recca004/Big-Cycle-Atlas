"""One-off coverage verification: latest-vintage matrix + ingestion health."""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, ".")

from sqlalchemy import and_, func, select, text

from app.db.session import get_sessionmaker
from app.models import Country, Indicator, Observation, SourceSeries


async def main() -> None:
    session = get_sessionmaker()()

    latest = (
        select(
            Observation.country_id,
            Observation.source_series_id,
            Observation.period_start,
            func.max(Observation.vintage_number).label("mv"),
        )
        .group_by(Observation.country_id, Observation.source_series_id, Observation.period_start)
        .subquery()
    )

    print("Coverage matrix (latest vintage only): country / indicator / years / latest")
    rows = (
        await session.execute(
            select(
                Country.iso3,
                Indicator.code,
                func.count().label("years"),
                func.max(Observation.period_start).label("latest"),
            )
            .select_from(Observation)
            .join(SourceSeries, SourceSeries.id == Observation.source_series_id)
            .join(Indicator, Indicator.id == SourceSeries.indicator_id)
            .join(Country, Country.id == Observation.country_id)
            .join(
                latest,
                and_(
                    Observation.country_id == latest.c.country_id,
                    Observation.source_series_id == latest.c.source_series_id,
                    Observation.period_start == latest.c.period_start,
                    Observation.vintage_number == latest.c.mv,
                ),
            )
            .group_by(Country.iso3, Indicator.code)
            .order_by(Country.iso3, Indicator.code)
        )
    ).all()
    for row in rows:
        print(f"  {row[0]}  {row[1]:<16} years={row[2]:>2}  latest={row[3]}")

    totals = (
        await session.execute(
            select(
                func.count(),
                func.min(Observation.vintage_number),
                func.max(Observation.vintage_number),
                func.count(func.distinct(Observation.country_id)),
            )
        )
    ).one()
    print(f"\nAll vintages: total={totals[0]}  countries={totals[3]}  "
          f"vintage range={totals[1]}..{totals[2]}")

    runs = (
        await session.execute(text(
            "SELECT status, count(*) FROM ingestion_runs GROUP BY status ORDER BY status"
        ))
    ).all()
    print("\nIngestionRun health:")
    for status, count in runs:
        print(f"  {status}: {count}")

    await session.close()


if __name__ == "__main__":
    asyncio.run(main())