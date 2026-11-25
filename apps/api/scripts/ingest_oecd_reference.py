"""Ingest an OECD calibration reference universe (DEC-042, Sprint 6.14).

Fetches the full cross-country distribution for the named universe's series
in ONE wildcard request, validates the non-country SDMX dimensions, filters
rows to the universe membership, and stores them in reference_observations.

Usage:
    uv run python scripts/ingest_oecd_reference.py [--universe oecd_lpph_v1]
        [--start-year 1990] [--end-year 2025]

Idempotent: a re-run of an identical period writes a higher vintage_number,
matching the observations table's revision semantics.
"""
import argparse
import asyncio
import csv
import io
import sys
from datetime import datetime, timezone, date

sys.path.insert(0, ".")

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import func, select

from app.data_sources.oecd import OECDAdapter
from app.data_sources.oecd_mappings import get_oecd_mapping_by_external_code
from app.data_sources.base import DataSourceParseError
from app.cycle.reference_universes import get_reference_universe
from app.db.base import Base
from app.db.models import ReferenceObservation
from app.db.session import get_engine, get_sessionmaker


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default="oecd_lpph_v1")
    parser.add_argument("--start-year", type=int, default=1990)
    parser.add_argument("--end-year", type=int, default=2030)
    args = parser.parse_args()

    universe = get_reference_universe(args.universe)
    if universe is None:
        raise SystemExit(f"unknown reference universe {args.universe!r}")
    mapping = get_oecd_mapping_by_external_code(universe.external_code)
    if mapping is None:
        raise SystemExit(f"unmapped external code {universe.external_code!r}")

    retrieved_at = datetime.now(timezone.utc)
    async with OECDAdapter() as adapter:
        payload = await adapter.fetch_universe_csv(
            universe.external_code, args.start_year, args.end_year
        )

    reader = csv.DictReader(io.StringIO(payload))
    rows = [r for r in reader if r is not None]

    written = 0
    skipped_nonmember: set[str] = set()
    # Ensure the table exists (create_all is additive, non-destructive).
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with get_sessionmaker()() as session:
        for row in rows:
            iso3 = (row.get("REF_AREA") or "").strip()
            if iso3 not in universe.expected_member_iso3:
                skipped_nonmember.add(iso3)  # aggregates (OECD, OEU...) — excluded
                continue
            raw_value = (row.get("OBS_VALUE") or "").strip()
            if raw_value == "":
                continue
            # Validate every non-country expected dimension.
            for column, expected in mapping.expected_dims:
                if column not in row or column == "REF_AREA":
                    continue
                actual = (row.get(column) or "").strip()
                if actual != expected:
                    raise DataSourceParseError(
                        f"OECD universe row identity violation: expected "
                        f"{column}={expected!r} but got {column}={actual!r} "
                        f"({universe.external_code})"
                    )
            year = int((row.get("TIME_PERIOD") or "").strip()[:4])
            if not (args.start_year <= year <= args.end_year):
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
                    value=float(raw_value),
                    unit=mapping.external_unit,
                    source_key=universe.source_key,
                    external_code=universe.external_code,
                    retrieved_at=retrieved_at,
                    vintage_number=(existing_vintage or 0) + 1,
                    raw_payload=dict(row),
                )
            )
            written += 1
        await session.commit()
    print(
        f"{universe.universe_code}: wrote {written} reference observations; "
        f"excluded non-member codes: {sorted(skipped_nonmember) or 'none'}"
    )


if __name__ == "__main__":
    asyncio.run(main())
