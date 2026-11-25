"""Bulk WDI international-power expansion for the tracked countries.

Uses World Bank `country=all` series endpoints once per series, filters to the
canonical tracked-country set, and persists through `persist_observations`.
This avoids one request per country and keeps missing provider values absent.
"""
import argparse
import asyncio
import sys
from datetime import date, datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.data_sources.base import ObservationDTO
from app.data_sources.world_bank import WorldBankAdapter
from app.data_sources.world_bank_mappings import get_world_bank_mapping_by_external_code
from app.db.session import get_sessionmaker
from app.models import Country, DataSource, IngestionRun, IngestionRunStatus
from app.services.observation_service import persist_observations

TRACKED = {"USA", "CHN", "IND", "JPN", "DEU", "GBR", "FRA", "CHE"}
POWER_EXPANSION_EXTERNAL_CODES = (
    "NY.GDP.MKTP.PP.CD",
    "NY.GDP.MKTP.KD",
    "TX.VAL.MRCH.CD.WT",
    "TM.VAL.MRCH.CD.WT",
    "TX.VAL.SERV.CD.WT",
    "TM.VAL.SERV.CD.WT",
    "IP.PAT.RESD",
    "IP.PAT.NRES",
    "SP.POP.SCIE.RD.P6",
    "TX.VAL.TECH.CD",
    "CM.MKT.LCAP.GD.ZS",
    "FS.AST.PRVT.GD.ZS",
    "FM.LBL.BMNY.GD.ZS",
)


async def main() -> int:
    parser = argparse.ArgumentParser(description="Bulk WDI power-expansion import")
    parser.add_argument("--start", type=int, default=1980)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    codes = list(POWER_EXPANSION_EXTERNAL_CODES)
    adapter = WorldBankAdapter()
    total_inserted = total_received = total_skipped = total_revised = 0
    async with get_sessionmaker()() as session:
        countries = {
            row[0]
            for row in (
                await session.execute(select(Country.iso3))
            ).all()
        }
        countries &= TRACKED
        source = (
            await session.execute(select(DataSource).where(DataSource.key == "world_bank"))
        ).scalar_one()
        async with adapter:
            for code in codes:
                mapping = get_world_bank_mapping_by_external_code(code)
                if mapping is None:
                    continue
                run = IngestionRun(
                    data_source_id=source.id,
                    status=IngestionRunStatus.running,
                    run_metadata={
                        "kind": "wdi_power_expansion_bulk",
                        "external_series_code": code,
                        "start_year": args.start,
                        "end_year": args.end,
                    },
                )
                session.add(run)
                await session.flush()
                try:
                    records, _members = await adapter.fetch_universe_records(
                        code, start_year=args.start, end_year=args.end
                    )
                    dtos = []
                    for rec in records:
                        iso3 = (rec.get("countryiso3code") or "").upper()
                        year_raw = str(rec.get("date") or "")
                        if iso3 not in countries or rec.get("value") is None:
                            continue
                        if not (year_raw.isdigit() and len(year_raw) == 4):
                            continue
                        year = int(year_raw)
                        if year < args.start or (args.end and year > args.end):
                            continue
                        dtos.append(ObservationDTO(
                            country_iso3=iso3,
                            indicator_code=mapping.indicator_code,
                            external_series_code=code,
                            period=year,
                            value=float(rec["value"]),
                            unit=rec.get("unit") or None,
                            source_key="world_bank",
                            observation_date=date(year, 1, 1),
                            release_date=None,
                            retrieved_at=datetime.now(timezone.utc),
                            raw_payload=rec,
                        ))
                    result = await persist_observations(session, dtos)
                    run.status = IngestionRunStatus.success
                    run.completed_at = datetime.now(timezone.utc)
                    run.rows_received = result.received
                    run.rows_inserted = result.inserted
                    run.rows_skipped = result.skipped
                    run.rows_revised = result.revised
                    await session.commit()
                    total_received += result.received
                    total_inserted += result.inserted
                    total_skipped += result.skipped
                    total_revised += result.revised
                    print(f"{code}: {result.inserted} inserted / {result.received} received")
                except Exception as exc:
                    await session.rollback()
                    run = IngestionRun(
                        data_source_id=source.id,
                        status=IngestionRunStatus.failed,
                        completed_at=datetime.now(timezone.utc),
                        error_count=1,
                        errors={"type": type(exc).__name__, "message": str(exc)},
                        run_metadata={"external_series_code": code},
                    )
                    session.add(run)
                    await session.commit()
                    print(f"{code}: failed {type(exc).__name__}: {exc}")
        print(
            f"Power expansion complete: {total_inserted} inserted, "
            f"{total_skipped} skipped, {total_revised} revised "
            f"from {total_received} received rows"
        )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
