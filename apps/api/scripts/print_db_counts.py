"""Print final database counts for Sprint 5.20 documentation."""
import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select, func

from app.db.session import get_sessionmaker
from app.models import Observation, Indicator, SourceSeries, DataSource, IndicatorDiagnostic


async def main():
    sm = get_sessionmaker()
    async with sm() as session:
        obs_count = (await session.execute(
            select(func.count()).select_from(Observation)
        )).scalar_one()
        ind_count = (await session.execute(
            select(func.count()).select_from(Indicator)
        )).scalar_one()
        ss_count = (await session.execute(
            select(func.count()).select_from(SourceSeries)
        )).scalar_one()
        ds_count = (await session.execute(
            select(func.count()).select_from(DataSource)
        )).scalar_one()
        diag_count = (await session.execute(
            select(func.count()).select_from(IndicatorDiagnostic)
        )).scalar_one()

        # Per-source observation counts
        from app.models import Country
        from sqlalchemy import text
        result = await session.execute(text("""
            SELECT ds.key, COUNT(o.id) as obs_count
            FROM observations o
            JOIN source_series ss ON o.source_series_id = ss.id
            JOIN data_sources ds ON ss.data_source_id = ds.id
            GROUP BY ds.key
            ORDER BY ds.key
        """))
        per_source = result.all()

        # Per-indicator observation counts for new indicators
        result2 = await session.execute(text("""
            SELECT i.code, c.iso3, COUNT(o.id) as cnt,
                   MIN(o.observation_date) as first_date,
                   MAX(o.observation_date) as latest_date
            FROM observations o
            JOIN source_series ss ON o.source_series_id = ss.id
            JOIN indicators i ON ss.indicator_id = i.id
            JOIN countries c ON o.country_id = c.id
            WHERE i.code IN ('TERTIARY_ATTAINMENT_25_34', 'WEALTH_SHARE_TOP_10', 'GOVERNMENT_DEBT_GDP')
            GROUP BY i.code, c.iso3
            ORDER BY i.code, c.iso3
        """))
        per_indicator = result2.all()

    print(f"Observations: {obs_count}")
    print(f"Indicators: {ind_count}")
    print(f"SourceSeries: {ss_count}")
    print(f"DataSources: {ds_count}")
    print(f"IndicatorDiagnostics: {diag_count}")
    print()
    print("Per-source observation counts:")
    for key, cnt in per_source:
        print(f"  {key}: {cnt}")
    print()
    print("New indicators per-country:")
    for code, iso3, cnt, first, latest in per_indicator:
        print(f"  {code} / {iso3}: {cnt} obs, {first} to {latest}")


if __name__ == "__main__":
    asyncio.run(main())
