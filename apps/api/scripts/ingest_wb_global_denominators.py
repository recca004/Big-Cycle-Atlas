"""Ingest WDI world totals used as international-power denominators.

World rows are stored in `reference_observations`, not `observations`, so the
aggregate entity never becomes a ninth tracked country and never enters force
coverage or domestic-condition calculations.
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app.data_sources.world_bank import WorldBankAdapter
from app.db.session import get_sessionmaker
from app.models import DataSource, IngestionRun, IngestionRunStatus, ReferenceObservation
from app.research.power_registry import GLOBAL_DENOMINATOR_SERIES

UNIVERSE = "world_wdi_denominator_v1"


async def main() -> int:
    parser = argparse.ArgumentParser(description="WDI global denominator import")
    parser.add_argument("--start", type=int, default=1980)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    async with get_sessionmaker()() as session:
        source = (
            await session.execute(
                select(DataSource).where(DataSource.key == "world_bank")
            )
        ).scalar_one()
        run = IngestionRun(
            data_source_id=source.id,
            status=IngestionRunStatus.running,
            run_metadata={
                "kind": "reference_denominator",
                "universe_code": UNIVERSE,
                "entity": "WLD",
            },
        )
        session.add(run)
        await session.flush()

        inserted = received = skipped = 0
        adapter = WorldBankAdapter()
        try:
            async with adapter:
                for external_code, spec in GLOBAL_DENOMINATOR_SERIES.items():
                    dtos = await adapter.fetch_indicator(
                        spec["entity"],
                        external_code,
                        start_year=args.start,
                        end_year=args.end,
                    )
                    received += len(dtos)
                    for dto in dtos:
                        period_start = datetime(
                            dto.period, 1, 1, tzinfo=timezone.utc
                        )
                        existing_vintage = (
                            await session.execute(
                                select(func.max(ReferenceObservation.vintage_number)).where(
                                    ReferenceObservation.universe_code == UNIVERSE,
                                    ReferenceObservation.indicator_code == spec["indicator_code"],
                                    ReferenceObservation.country_iso3 == spec["entity"],
                                    ReferenceObservation.period_start == period_start,
                                )
                            )
                        ).scalar()
                        session.add(
                            ReferenceObservation(
                                universe_code=UNIVERSE,
                                indicator_code=spec["indicator_code"],
                                country_iso3=spec["entity"],
                                period_start=period_start,
                                period_end=datetime(
                                    dto.period, 12, 31, tzinfo=timezone.utc
                                ),
                                value=dto.value,
                                unit=dto.unit or "current US$",
                                source_key="world_bank",
                                external_code=external_code,
                                retrieved_at=dto.retrieved_at,
                                vintage_number=(existing_vintage or 0) + 1,
                                raw_payload=dto.raw_payload,
                            )
                        )
                        inserted += 1
            run.status = IngestionRunStatus.success
            run.rows_received = received
            run.rows_inserted = inserted
            run.rows_skipped = skipped
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()
            print(
                f"{UNIVERSE}: received {received}, wrote {inserted} "
                f"reference rows across {len(GLOBAL_DENOMINATOR_SERIES)} series"
            )
            return 0
        except Exception as exc:
            await session.rollback()
            run.status = IngestionRunStatus.failed
            run.error_count = 1
            run.errors = {"error": str(exc)}
            run.completed_at = datetime.now(timezone.utc)
            session.add(run)
            await session.commit()
            raise


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
