"""Import official ALFRED real-time vintages into research_observations.

Usage:
    python scripts/ingest_alfred.py GDP CPIAUCSL

Set BCA_FRED_API_KEY to a registered FRED API key. Without the key the command
reports the precise credential blocker and imports nothing.
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.path.insert(0, ".")

from sqlalchemy import select

from app.data_sources.alfred import AlfredAdapter, ALFRED_SOURCE_KEY
from app.data_sources.base import DataSourceCredentialError
from app.db.session import get_sessionmaker
from app.models import ResearchObservation


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("series", nargs="+", help="FRED series IDs")
    parser.add_argument(
        "--vintages", type=int, default=3,
        help="number of most recent official vintages to import per series; -1 imports all",
    )
    args = parser.parse_args()
    adapter = AlfredAdapter()
    try:
        selected_vintages = {}
        for series in args.series:
            dates = await adapter.vintage_dates(series)
            selected_vintages[series] = (
                dates if args.vintages < 0 else dates[-args.vintages:] if args.vintages else []
            )
        observations = {
            (series, vintage): await adapter.observations(series, vintage_date=vintage)
            for series, vintages in selected_vintages.items()
            for vintage in vintages
        }
        vintage_counts = {k: len(v) for k, v in selected_vintages.items()}
    except DataSourceCredentialError as exc:
        print({"status": "blocked", "reason": str(exc), "imported": 0})
        return

    session = get_sessionmaker()()
    retrieved = datetime.now(timezone.utc)
    async with session.begin():
        existing = {
            (r.source_key, r.entity_code, r.variable_code, r.period_start, r.vintage_date)
            for r in (await session.execute(select(
                ResearchObservation.source_key, ResearchObservation.entity_code,
                ResearchObservation.variable_code, ResearchObservation.period_start,
                ResearchObservation.vintage_date,
            ).where(ResearchObservation.source_key == ALFRED_SOURCE_KEY))).all()
        }
        inserted = 0
        for (series, vintage), rows in observations.items():
            for row in rows:
                key = (ALFRED_SOURCE_KEY, "USA", series, datetime(row.observation_date.year,row.observation_date.month,row.observation_date.day,tzinfo=timezone.utc), row.realtime_start)
                if key in existing:
                    continue
                session.add(ResearchObservation(
                    source_key=ALFRED_SOURCE_KEY,
                    dataset_version=f"vintage:{row.realtime_start.isoformat()}",
                    entity_code="USA", entity_name="United States", entity_type="country",
                    variable_code=series, variable_name=series,
                    period_start=key[3], value=row.value, unit=row.unit,
                    vintage_date=row.realtime_start,
                    release_date=datetime(row.realtime_start.year,row.realtime_start.month,row.realtime_start.day,tzinfo=timezone.utc),
                    release_evidence_type="provider_vintage_realtime_start",
                    retrieved_at=retrieved,
                    source_version="FRED API / ALFRED realtime",
                    source_url=f"https://fred.stlouisfed.org/series/{series}",
                    license_code="FRED API terms",
                    raw_payload={"realtime_end": row.realtime_end.isoformat(), "observation": row.raw_payload},
                ))
                existing.add(key); inserted += 1
    print({"status": "imported", "vintage_dates": vintage_counts, "observations_inserted": inserted})


if __name__ == "__main__":
    asyncio.run(main())
