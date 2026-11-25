"""Prospective evidence collection (Mission 5 §7).

Re-fetches every mapped series for every tracked country through the
normal ingestion path. Each call records an IngestionRun with a
content_sha256 checksum; changed values become NEW vintages (never
overwrites), unchanged values are skipped. Every observation row carries
retrieved_at = the first-observed timestamp for its vintage — sound
conservative evidence that the exact value existed by that timestamp,
usable by strict_as_of in addition to provider release_date.

Run it on any schedule — manual, Task Scheduler, cron. No paid service.

    python scripts/collect_snapshot.py                  # all providers
    python scripts/collect_snapshot.py --source world_bank
    python scripts/collect_snapshot.py --country USA --source world_bank
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.data_sources.bis import BISAdapter  # noqa: E402
from app.data_sources.bis_mappings import BIS_MAPPINGS  # noqa: E402
from app.data_sources.imf_weo import ImfWeoAdapter  # noqa: E402
from app.data_sources.imf_weo_mappings import IMF_WEO_MAPPINGS  # noqa: E402
from app.data_sources.oecd import OECDAdapter  # noqa: E402
from app.data_sources.oecd_mappings import OECD_MAPPINGS  # noqa: E402
from app.data_sources.wid import WidAdapter  # noqa: E402
from app.data_sources.wid_mappings import WID_MAPPINGS  # noqa: E402
from app.data_sources.world_bank import WorldBankAdapter  # noqa: E402
from app.data_sources.world_bank_mappings import WORLD_BANK_MAPPINGS  # noqa: E402
from app.db.session import get_sessionmaker  # noqa: E402
from app.models import Country  # noqa: E402
from app.services.ingestion_service import run_ingestion  # noqa: E402

# source_key -> (adapter class, mapping registry)
PROVIDERS = {
    "world_bank": (WorldBankAdapter, WORLD_BANK_MAPPINGS),
    "bis": (BISAdapter, BIS_MAPPINGS),
    "oecd": (OECDAdapter, OECD_MAPPINGS),
    "imf_weo": (ImfWeoAdapter, IMF_WEO_MAPPINGS),
    # WID is a file-based provider: it needs the ~882MB bulk archive, not a live
    # call. Include it via --wid-zip, or refresh it with scripts/ingest_wid.py.
}


async def _countries(only: str | None) -> list[str]:
    if only:
        return [only]
    async with get_sessionmaker()() as session:
        rows = await session.execute(select(Country.iso3).order_by(Country.iso3))
        return [r[0] for r in rows.all()]


async def _ingest_one(
    adapter, country: str, external_code: str, max_429_retries: int = 1
) -> str:
    """Ingest a single series for a single country.

    HTTP 429 (provider rate limiting) gets ONE bounded retry after a long
    backoff — never a retry storm. Previous valid observations are never
    touched by a failed run (immutable vintages), and the failed run is
    still recorded honestly as failed."""
    for attempt in range(max_429_retries + 1):
        session = get_sessionmaker()()
        try:
            outcome = await run_ingestion(
                session, adapter,
                country_iso3=country, external_series_code=external_code,
            )
            await session.commit()
            if outcome.error:
                if "429" in outcome.error and attempt < max_429_retries:
                    # OECD publishes a ~60 queries/hour ceiling; back off
                    # well past the rolling window edge, once.
                    await asyncio.sleep(65)
                    continue
                return f"FAIL:{outcome.error.split(':')[0]}"
            p = outcome.persistence
            if p is None:
                return "FAIL"
            if p.revised:
                return f"REVISED({p.revised})"
            if p.inserted:
                return f"NEW({p.inserted})"
            return "same"
        except Exception as exc:  # identity errors must not abort the snapshot
            await session.rollback()
            return f"ERROR:{type(exc).__name__}"
        finally:
            await session.close()
    return "FAIL"


async def main() -> int:
    parser = argparse.ArgumentParser(description="Prospective evidence snapshot")
    parser.add_argument(
        "--source", choices=list(PROVIDERS) + ["wid"], default=None
    )
    parser.add_argument("--country", default=None, help="ISO3 code")
    parser.add_argument(
        "--wid-zip", type=Path, default=None,
        help="Pre-downloaded WID bulk archive (enables the wid provider)",
    )
    args = parser.parse_args()

    countries = await _countries(args.country)
    providers = dict(PROVIDERS)
    if args.wid_zip:
        providers["wid"] = (WidAdapter, WID_MAPPINGS)
    if args.source == "wid" and not args.wid_zip:
        print("wid: skipped (bulk-file provider; pass --wid-zip or use ingest_wid.py)")
        return 0
    if args.source:
        providers = {args.source: providers[args.source]}

    summary: dict[str, int] = {}
    for source_key, (adapter_cls, mappings) in providers.items():
        codes = [m.external_code for m in mappings]
        print(f"{source_key}: {len(codes)} series x {len(countries)} countries")
        adapter = adapter_cls(zip_path=args.wid_zip) if source_key == "wid" else adapter_cls()
        async with adapter:
            # Throttle providers with published rate ceilings (OECD ~60qph).
            throttle = 1.5 if source_key == "oecd" else 0.0
            for code in codes:
                for country in countries:
                    status = await _ingest_one(adapter, country, code)
                    summary[status.split("(")[0]] = (
                        summary.get(status.split("(")[0], 0) + 1
                    )
                    if not status.startswith("same"):
                        print(f"  {country} {code}: {status}")
                    if throttle:
                        await asyncio.sleep(throttle)
    print("\nSnapshot complete:", summary)
    # Snapshot is still a success if every run was merely 'same'.
    failures = sum(v for k, v in summary.items() if k in {"FAIL", "ERROR"})
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
