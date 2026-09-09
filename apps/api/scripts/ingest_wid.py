"""Live WID import through the full ingestion path.

Fetches mapped indicator(s) via WidAdapter (bulk download zip), persists the
DTOs, and records one IngestionRun per country × indicator — each in its own
caller-owned transaction.

    python scripts/ingest_wid.py --country USA --all-mapped
    python scripts/ingest_wid.py --all-countries --all-mapped

The WID bulk download is a single 882 MB zip archive. The script downloads
it once (cached to a local temp file) and extracts per-country CSV files.
No API key required (verified 2026-09-10).
"""
import argparse
import asyncio
import sys
import tempfile
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import select

from app.data_sources.base import DataSourceError
from app.data_sources.wid import DEFAULT_BULK_URL, WidAdapter
from app.data_sources.wid_mappings import WID_MAPPINGS, get_wid_mapping
from app.db.session import get_sessionmaker
from app.models import Country
from app.services.ingestion_service import run_ingestion


async def download_bulk_zip(dest: Path) -> None:
    """Download the WID bulk archive (882 MB) to dest."""
    print(f"Downloading WID bulk archive from {DEFAULT_BULK_URL} ...")
    async with httpx.AsyncClient(timeout=600, follow_redirects=True) as client:
        async with client.stream("GET", DEFAULT_BULK_URL) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                async for chunk in response.aiter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded * 100 / total
                        print(f"\r  {downloaded / 1e6:.1f} / {total / 1e6:.1f} MB ({pct:.1f}%)", end="", flush=True)
            print()
    print(f"Download complete: {dest} ({dest.stat().st_size / 1e6:.1f} MB)")


async def tracked_country_iso3s() -> list[str]:
    session = get_sessionmaker()()
    try:
        rows = await session.execute(select(Country.iso3).order_by(Country.iso3))
        return [row[0] for row in rows.all()]
    finally:
        await session.close()


async def import_one(adapter: WidAdapter, country: str, indicator_code: str,
                     start: int | None, end: int | None) -> dict:
    mapping = get_wid_mapping(indicator_code)
    if mapping is None:
        print(f"[{country} / {indicator_code}] No WID mapping — skipped.")
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
        await session.commit()
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
    parser = argparse.ArgumentParser(description="WID live import")
    parser.add_argument("--country", default=None, help="ISO3 code")
    parser.add_argument("--all-countries", action="store_true",
                        help="Import for every country in the seeded Country table")
    parser.add_argument("--indicator", default=None, help="Canonical indicator code")
    parser.add_argument("--all-mapped", action="store_true",
                        help="Import every indicator in the WID mapping registry")
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--zip-path", default=None,
                        help="Path to a pre-downloaded WID bulk zip (skips download)")
    args = parser.parse_args()

    if args.all_countries:
        countries = await tracked_country_iso3s()
    elif args.country:
        countries = [args.country]
    else:
        countries = ["CHE"]

    if args.all_mapped:
        indicator_codes = [m.indicator_code for m in WID_MAPPINGS]
    elif args.indicator:
        indicator_codes = [args.indicator]
    else:
        indicator_codes = ["WEALTH_SHARE_TOP_10"]

    # Resolve zip path
    if args.zip_path:
        zip_path = Path(args.zip_path)
        if not zip_path.exists():
            print(f"ERROR: zip file not found: {zip_path}")
            return 1
    else:
        tmp_dir = Path(tempfile.gettempdir())
        zip_path = tmp_dir / "wid_all_data.zip"
        if not zip_path.exists():
            await download_bulk_zip(zip_path)

    span = f"{args.start or 'all'}–{args.end or 'now'}"
    print(f"\nWID batch import: {len(countries)} countries × "
          f"{len(indicator_codes)} indicators · {span}\n")

    totals = {"attempted": 0, "succeeded": 0, "failed": 0,
              "received": 0, "inserted": 0, "skipped": 0, "revised": 0}
    failures: list[str] = []

    adapter = WidAdapter(zip_path=zip_path)
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

    print("\nWID batch import")
    print("----------------")
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
