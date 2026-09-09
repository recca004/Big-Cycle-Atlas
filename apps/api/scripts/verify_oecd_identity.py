"""Verify the OECD education SourceSeries external_code was updated in the live DB."""
import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_engine


async def main():
    engine = get_engine()
    async with AsyncSession(engine) as session:
        result = await session.execute(
            text(
                "SELECT ds.key, ss.external_code "
                "FROM source_series ss "
                "JOIN data_sources ds ON ss.data_source_id = ds.id "
                "WHERE ds.key = 'oecd' "
                "ORDER BY ss.external_code"
            )
        )
        for row in result:
            print(f"{row[0]}: {row[1]}")

        # Also verify the education series length
        result2 = await session.execute(
            text(
                "SELECT ss.external_code, length(ss.external_code) "
                "FROM source_series ss "
                "JOIN data_sources ds ON ss.data_source_id = ds.id "
                "WHERE ds.key = 'oecd' AND ss.external_code LIKE '%Y25T34%'"
            )
        )
        for row in result2:
            print(f"\nEducation series length: {row[1]} chars")
            print(f"Exceeds 100: {row[1] > 100}")

        # Verify total SourceSeries count
        result3 = await session.execute(
            text("SELECT count(*) FROM source_series")
        )
        print(f"\nTotal SourceSeries: {result3.scalar()}")

        # Verify no duplicate education series
        result4 = await session.execute(
            text(
                "SELECT count(*) FROM source_series ss "
                "JOIN data_sources ds ON ss.data_source_id = ds.id "
                "WHERE ds.key = 'oecd' AND ss.external_code LIKE '%Y25T34%'"
            )
        )
        print(f"Education SourceSeries count: {result4.scalar()} (must be 1)")


if __name__ == "__main__":
    asyncio.run(main())
