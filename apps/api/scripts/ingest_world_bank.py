"""Live World Bank import through the full ingestion path (Micro-Sprint 3.5+).

Fetches mapped indicator(s) via WorldBankAdapter, persists the DTOs, and
records one IngestionRun per indicator import — each in its own caller-owned
transaction (committed only if that run succeeds).

    python scripts/ingest_world_bank.py --country CHE --all-mapped --start 2015 --end 2025
    python scripts/ingest_world_bank.py --all-countries --all-mapped --start 2015 --end 2025

--all-countries reads the tracked-country list from the seeded Country table
(canonical source, DEC-004). Transient network/5xx failures are retried up to
3 attempts total inside the run; 4xx, parse, and identity errors are not
retried. A failed series is recorded as a failed IngestionRun and never
aborts the batch.
"""
import argparse
import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.data_sources.base import (
    BaseDataSourceAdapter,
    DataSourceError,
    DataSourceHTTPError,
    DataSourceParseError,
    SeriesMappingError,
)
from app.data_sources.world_bank import WorldBankAdapter
from app.data_sources.world_bank_mappings import WORLD_BANK_MAPPINGS, get_world_bank_mapping
from app.db.session import get_sessionmaker
from app.models import Country
from app.services.ingestion_service import run_ingestion

MAX_ATTEMPTS = 3


class TransientRetryAdapter(BaseDataSourceAdapter):
    """Retries transient fetch failures (network / 5xx) up to MAX_ATTEMPTS.

    Wraps the real adapter, so run_ingestion sees at most one outcome per
    series — a failed attempt never creates an IngestionRun by itself.
    4xx, parse, and mapping errors are raised immediately.
    """

    def __init__(self, inner: BaseDataSourceAdapter, max_attempts: int = MAX_ATTEMPTS):
        self.inner = inner
        self.source_key = inner.source_key
        self.max_attempts = max_attempts

    async def fetch_indicator(self, country_iso3, external_series_code,
                              start_year=None, end_year=None):
        last: DataSourceError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await self.inner.fetch_indicator(
                    country_iso3, external_series_code,
                    start_year=start_year, end_year=end_year,
                )
            except DataSourceHTTPError as exc:
                if exc.status_code is not None and 400 <= exc.status_code < 500:
                    raise  # client error — retrying won't help
                last = exc
            except (DataSourceParseError, SeriesMappingError):
                raise
            except DataSourceError as exc:
                last = exc
            if attempt < self.max_attempts:
                await asyncio.sleep(2 * attempt)
        assert last is not None
        raise last


async def tracked_country_iso3s() -> list[str]:
    """Canonical tracked countries from the seeded Country table."""
    session = get_sessionmaker()()
    try:
        rows = await session.execute(select(Country.iso3).order_by(Country.iso3))
        return [row[0] for row in rows.all()]
    finally:
        await session.close()


async def import_one(adapter: BaseDataSourceAdapter, country: str, indicator_code: str,
                     start: int, end: int | None) -> dict:
    mapping = get_world_bank_mapping(indicator_code)
    if mapping is None:
        print(f"[{country} / {indicator_code}] No World Bank mapping — skipped.")
        return {"ok": False, "reason": "no mapping", "counts": (0, 0, 0, 0)}

    session = get_sessionmaker()()
    try:
        outcome = await run_ingestion(
            session,
            adapter,
            country_iso3=country,
            external_series_code=mapping.external_code,
            start_year=start,
            end_year=end,
        )
    except Exception as exc:
        await session.rollback()
        await session.close()
        print(f"[{country} / {indicator_code}] FAILED — transaction rolled back: "
              f"{type(exc).__name__}: {exc}")
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}",
                "counts": (0, 0, 0, 0)}

    run, p = outcome.run, outcome.persistence
    if outcome.error is not None:
        await session.commit()  # keep the failed-run record; nothing else was written
        print(f"[{country} / {indicator_code}] Run #{run.id}: FAILED — {outcome.error}")
        await session.close()
        return {"ok": False, "reason": outcome.error, "counts": (0, 0, 0, 0)}

    await session.commit()
    print(f"[{country} / {indicator_code}] Run #{run.id}: SUCCESS — "
          f"received {p.received}  inserted {p.inserted}  "
          f"skipped {p.skipped}  revised {p.revised}")
    await session.close()
    return {"ok": True, "reason": None, "counts": (p.received, p.inserted, p.skipped, p.revised)}


async def main() -> int:
    parser = argparse.ArgumentParser(description="World Bank live import")
    parser.add_argument("--country", default=None, help="ISO3 code")
    parser.add_argument("--all-countries", action="store_true",
                        help="Import for every country in the seeded Country table")
    parser.add_argument("--indicator", default=None, help="Canonical indicator code")
    parser.add_argument("--all-mapped", action="store_true",
                        help="Import every indicator in the central World Bank mapping registry")
    parser.add_argument("--start", type=int, default=2015)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    if args.all_countries:
        countries = await tracked_country_iso3s()
    elif args.country:
        countries = [args.country]
    else:
        countries = ["CHE"]

    if args.all_mapped:
        indicator_codes = [m.indicator_code for m in WORLD_BANK_MAPPINGS]
    elif args.indicator:
        indicator_codes = [args.indicator]
    else:
        indicator_codes = ["GDP_GROWTH"]

    span = f"{args.start}–{args.end or 'now'}"
    print(f"World Bank batch import: {len(countries)} countries × "
          f"{len(indicator_codes)} indicators · {span}\n")

    totals = {"attempted": 0, "succeeded": 0, "failed": 0,
              "received": 0, "inserted": 0, "skipped": 0, "revised": 0}
    failures: list[str] = []

    async with WorldBankAdapter() as wb:
        adapter = TransientRetryAdapter(wb)
        for country in countries:
            for code in indicator_codes:
                totals["attempted"] += 1
                result = await import_one(adapter, country, code, args.start, args.end)
                r, i, s, v = result["counts"]
                totals["received"] += r
                totals["inserted"] += i
                totals["skipped"] += s
                totals["revised"] += v
                if result["ok"]:
                    totals["succeeded"] += 1
                else:
                    totals["failed"] += 1
                    failures.append(f"{country} / {code} — {result['reason']}")

    print("\nWorld Bank batch import")
    print("-----------------------")
    print(f"Countries: {len(countries)}")
    print(f"Indicators: {len(indicator_codes)}")
    print(f"Series attempted: {totals['attempted']}")
    print(f"\nSucceeded: {totals['succeeded']}")
    print(f"Failed: {totals['failed']}")
    print(f"\nReceived: {totals['received']}")
    print(f"Inserted: {totals['inserted']}")
    print(f"Skipped: {totals['skipped']}")
    print(f"Revised: {totals['revised']}")
    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"  {failure}")
    return 1 if totals["failed"] else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))