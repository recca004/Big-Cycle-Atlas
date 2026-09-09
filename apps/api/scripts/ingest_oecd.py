"""Live OECD import through the full ingestion path.

Fetches mapped indicator(s) via OECDAdapter, persists the DTOs, and records
one IngestionRun per country × indicator — each in its own caller-owned
transaction (committed only if that run succeeds).

    python scripts/ingest_oecd.py --country CHE --all-mapped --start 1990 --end 2025
    python scripts/ingest_oecd.py --all-countries --all-mapped --start 1990 --end 2025

OECD documents a ~60 queries/hour rate limit, so the batch is strictly
sequential with a small delay between live requests (no retry-storming, no
parallelism). Transient network/5xx failures are retried up to 3 attempts
total with a short backoff; 4xx, parse, and mapping errors are not retried.
A country/series OECD itself reports as having no observations (404
NoRecordsFound — e.g. CHN and IND in the productivity dataflows) is a
legitimate no-data outcome, recorded as a clean no-data run, never a failure.
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
    DataSourceNoDataError,
    DataSourceParseError,
    SeriesMappingError,
)
from app.data_sources.oecd import OECDAdapter
from app.data_sources.oecd_mappings import OECD_MAPPINGS, get_oecd_mapping
from app.db.session import get_sessionmaker
from app.models import Country
from app.services.ingestion_service import run_ingestion

MAX_ATTEMPTS = 3
INTER_SERIES_DELAY_SECONDS = 1.0  # OECD documents ~60 queries/hour


class TransientRetryAdapter(BaseDataSourceAdapter):
    """Retries transient fetch failures (network / 5xx) up to MAX_ATTEMPTS.

    Wraps the real adapter, so run_ingestion sees at most one outcome per
    series — a failed attempt never creates an IngestionRun by itself.
    4xx, no-data, parse, and mapping errors are raised immediately.
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
            except (DataSourceNoDataError, DataSourceParseError, SeriesMappingError):
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
    mapping = get_oecd_mapping(indicator_code)
    if mapping is None:
        print(f"[{country} / {indicator_code}] No OECD mapping — skipped.")
        return {"ok": False, "no_data": False, "reason": "no mapping",
                "counts": (0, 0, 0, 0)}

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
        return {"ok": False, "no_data": False,
                "reason": f"{type(exc).__name__}: {exc}",
                "counts": (0, 0, 0, 0)}

    run, p = outcome.run, outcome.persistence
    if outcome.error is not None:
        await session.commit()  # keep the failed-run record; nothing else was written
        print(f"[{country} / {indicator_code}] Run #{run.id}: FAILED — {outcome.error}")
        await session.close()
        return {"ok": False, "no_data": False, "reason": outcome.error,
                "counts": (0, 0, 0, 0)}

    await session.commit()
    if (run.run_metadata or {}).get("no_data") or p.received == 0:
        print(f"[{country} / {indicator_code}] Run #{run.id}: NO DATA — "
              "OECD reports no observations for this series (legitimate "
              "no coverage, not a failure)")
        await session.close()
        return {"ok": True, "no_data": True, "reason": None,
                "counts": (0, 0, 0, 0)}
    print(f"[{country} / {indicator_code}] Run #{run.id}: SUCCESS — "
          f"received {p.received}  inserted {p.inserted}  "
          f"skipped {p.skipped}  revised {p.revised}")
    await session.close()
    return {"ok": True, "no_data": False, "reason": None,
            "counts": (p.received, p.inserted, p.skipped, p.revised)}


async def main() -> int:
    parser = argparse.ArgumentParser(description="OECD live import")
    parser.add_argument("--country", default=None, help="ISO3 code")
    parser.add_argument("--all-countries", action="store_true",
                        help="Import for every country in the seeded Country table")
    parser.add_argument("--indicator", default=None, help="Canonical indicator code")
    parser.add_argument("--all-mapped", action="store_true",
                        help="Import every indicator in the central OECD mapping registry")
    parser.add_argument("--start", type=int, default=1990)
    parser.add_argument("--end", type=int, default=2025)
    args = parser.parse_args()

    if args.all_countries:
        countries = await tracked_country_iso3s()
    elif args.country:
        countries = [args.country]
    else:
        countries = ["CHE"]

    if args.all_mapped:
        indicator_codes = [m.indicator_code for m in OECD_MAPPINGS]
    elif args.indicator:
        indicator_codes = [args.indicator]
    else:
        indicator_codes = ["LABOUR_PRODUCTIVITY_PER_HOUR"]

    span = f"{args.start}–{args.end or 'now'}"
    print(f"OECD batch import: {len(countries)} countries × "
          f"{len(indicator_codes)} indicators · {span} · sequential, "
          f"{INTER_SERIES_DELAY_SECONDS:.0f}s between requests\n")

    totals = {"attempted": 0, "succeeded": 0, "no_data": 0, "failed": 0,
              "received": 0, "inserted": 0, "skipped": 0, "revised": 0}
    failures: list[str] = []

    async with OECDAdapter() as oecd:
        adapter = TransientRetryAdapter(oecd)
        first_request = True
        for country in countries:
            for code in indicator_codes:
                if not first_request:
                    await asyncio.sleep(INTER_SERIES_DELAY_SECONDS)
                first_request = False
                totals["attempted"] += 1
                result = await import_one(adapter, country, code, args.start, args.end)
                r, i, s, v = result["counts"]
                totals["received"] += r
                totals["inserted"] += i
                totals["skipped"] += s
                totals["revised"] += v
                if result["no_data"]:
                    totals["no_data"] += 1
                elif result["ok"]:
                    totals["succeeded"] += 1
                else:
                    totals["failed"] += 1
                    failures.append(f"{country} / {code} — {result['reason']}")

    print("\nOECD batch import")
    print("-----------------")
    print(f"Countries: {len(countries)}")
    print(f"Indicators: {len(indicator_codes)}")
    print(f"Series attempted: {totals['attempted']}")
    print(f"Data-bearing successes: {totals['succeeded']}")
    print(f"No-data (legitimate no coverage): {totals['no_data']}")
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