"""Ingest a World Bank reference universe into ReferenceObservation.

V1 Mission 1: populates `wdi_lfp_v1` (all WDI economies, aggregates
excluded via the WB country catalog region filter) for the labour-force
participation reference distribution.

Idempotent: a re-run writes a higher vintage_number; prior vintages are
preserved (matches ingest_oecd_reference.py semantics).
"""
import asyncio
import sys
from datetime import datetime, timezone

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, ".")

from sqlalchemy import func, select

from app.cycle.reference_universes import REFERENCE_UNIVERSES
from app.data_sources.world_bank import WorldBankAdapter
from app.db.session import get_sessionmaker
from app.models.reference_observation import ReferenceObservation


async def main(universe_code: str, start_year: int = 1990, end_year: int = 2100) -> None:
    universe = REFERENCE_UNIVERSES[universe_code]
    adapter = WorldBankAdapter()
    records, members = await adapter.fetch_universe_records(
        universe.external_code, start_year=start_year, end_year=end_year
    )
    print(f"WB returned {len(records)} raw records; {len(members)} member economies")
    retrieved_at = datetime.now(timezone.utc)
    written = 0
    skipped_nonmember: set[str] = set()
    async with get_sessionmaker()() as session:
        for rec in records:
            iso3 = (rec.get("countryiso3code") or "").strip().upper()
            if not iso3:
                continue
            if iso3 not in members:
                skipped_nonmember.add(iso3)  # aggregates — excluded
                continue
            if rec.get("value") is None:
                continue
            year_raw = str(rec.get("date", "")).strip()
            if not (year_raw.isdigit() and len(year_raw) == 4):
                continue
            year = int(year_raw)
            if not (start_year <= year <= end_year):
                continue
            period_start = datetime(year, 1, 1, tzinfo=timezone.utc)
            existing_vintage = (
                await session.execute(
                    select(func.max(ReferenceObservation.vintage_number)).where(
                        ReferenceObservation.universe_code == universe.universe_code,
                        ReferenceObservation.indicator_code == universe.indicator_code,
                        ReferenceObservation.country_iso3 == iso3,
                        ReferenceObservation.period_start == period_start,
                    )
                )
            ).scalar()
            session.add(
                ReferenceObservation(
                    universe_code=universe.universe_code,
                    indicator_code=universe.indicator_code,
                    country_iso3=iso3,
                    period_start=period_start,
                    period_end=datetime(year, 12, 31, tzinfo=timezone.utc),
                    value=float(rec["value"]),
                    unit=rec.get("unit") or "percent",
                    source_key=universe.source_key,
                    external_code=universe.external_code,
                    retrieved_at=retrieved_at,
                    vintage_number=(existing_vintage or 0) + 1,
                    raw_payload=dict(rec),
                )
            )
            written += 1
        await session.commit()
    print(f"{universe_code}: {written} rows written; "
          f"{len(skipped_nonmember)} aggregate codes skipped")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "wdi_lfp_v1"))
