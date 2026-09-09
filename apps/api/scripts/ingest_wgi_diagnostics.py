"""Live WGI diagnostic import (Sprint 5.15) — AUXILIARY data path.

Fetches the owner-approved WGI uncertainty diagnostic series (the 9 specs
in WGI_DIAGNOSTIC_SPECS: 3 WGI dimensions x LB/UB/SR) from the dedicated
WB WGI source (id 3), persists ONLY into `indicator_diagnostics` via
`persist_indicator_diagnostics`, and records one IngestionRun per
country x diagnostic series — each in its own caller-owned transaction
(committed only if that run succeeds).

    uv run --no-sync python scripts/ingest_wgi_diagnostics.py \
        --all-countries --all-indicators --all-kinds --start 1996 --end 2025

Deliberately SEPARATE from scripts/ingest_world_bank.py: that CLI imports
canonical economic observations; this one never touches the observation
persistence path. Transient network/5xx failures are retried up to 3
attempts total inside the run; 4xx, parse, and provider/spec identity
errors are not retried. A failed diagnostic series is recorded as a
failed IngestionRun and never aborts the batch.
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
    DataSourceError,
    DataSourceHTTPError,
    DataSourceParseError,
    SeriesMappingError,
)
from app.data_sources.world_bank_wgi_diagnostics import WorldBankWgiDiagnosticFetcher
from app.data_sources.wgi_diagnostic_specs import (
    WGI_BASE_INDICATORS,
    WGI_DIAGNOSTIC_SPECS,
    WgiDiagnosticSpec,
)
from app.db.session import get_sessionmaker
from app.models import Country, IndicatorDiagnosticKind
from app.services.wgi_diagnostic_ingestion import run_wgi_diagnostic_ingestion

MAX_ATTEMPTS = 3


class TransientRetryFetcher:
    """Retries transient fetch failures (network / 5xx) up to MAX_ATTEMPTS.

    Wraps the real fetcher, so the ingestion service sees at most one
    outcome per series — a failed attempt never creates an IngestionRun
    by itself. 4xx, parse, and provider/spec identity errors are raised
    immediately.
    """

    def __init__(self, inner, max_attempts: int = MAX_ATTEMPTS):
        self.inner = inner
        self.source_key = inner.source_key
        self.max_attempts = max_attempts

    async def fetch_wgi_diagnostic(self, country_iso3, spec, start_year=None,
                                  end_year=None):
        last: DataSourceError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return await self.inner.fetch_wgi_diagnostic(
                    country_iso3, spec, start_year=start_year, end_year=end_year,
                )
            except DataSourceHTTPError as exc:
                if exc.status_code is not None and 400 <= exc.status_code < 500:
                    raise  # client error — retrying won't help
                last = exc
            except (DataSourceParseError, SeriesMappingError):
                raise  # parse / provider-spec identity mismatch — never retried
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


async def import_one(fetcher, country: str, spec: WgiDiagnosticSpec,
                     start: int, end: int | None) -> dict:
    session = get_sessionmaker()()
    try:
        outcome = await run_wgi_diagnostic_ingestion(
            session, fetcher, country_iso3=country, spec=spec,
            start_year=start, end_year=end,
        )
    except Exception as exc:
        await session.rollback()
        await session.close()
        print(f"[{country} / {spec.provider_series_code}] FAILED — transaction "
              f"rolled back: {type(exc).__name__}: {exc}")
        return {"ok": False, "reason": f"{type(exc).__name__}: {exc}",
                "counts": (0, 0, 0, 0)}

    run, p = outcome.run, outcome.persistence
    if outcome.error is not None:
        await session.commit()  # keep the failed-run record; nothing else was written
        print(f"[{country} / {spec.provider_series_code}] Run #{run.id}: FAILED — "
              f"{outcome.error}")
        await session.close()
        return {"ok": False, "reason": outcome.error, "counts": (0, 0, 0, 0)}

    await session.commit()
    print(f"[{country} / {spec.provider_series_code}] Run #{run.id}: SUCCESS — "
          f"received {p.received}  inserted {p.inserted}  "
          f"skipped {p.skipped}  revised {p.revised}")
    await session.close()
    return {"ok": True, "reason": None,
            "counts": (p.received, p.inserted, p.skipped, p.revised)}


async def main() -> int:
    parser = argparse.ArgumentParser(
        description="WGI diagnostic live import (auxiliary indicator_diagnostics)"
    )
    parser.add_argument("--country", default=None, help="ISO3 code")
    parser.add_argument("--all-countries", action="store_true",
                        help="Import for every country in the seeded Country table")
    parser.add_argument("--indicator", default=None,
                        help="WGI base indicator code "
                             f"(one of {', '.join(WGI_BASE_INDICATORS)})")
    parser.add_argument("--all-indicators", action="store_true",
                        help="Import all 3 WGI base indicators")
    parser.add_argument("--kind", default=None,
                        choices=[kind.value for kind in IndicatorDiagnosticKind],
                        help="Diagnostic kind to import")
    parser.add_argument("--all-kinds", action="store_true",
                        help="Import all 3 diagnostic kinds (LB, UB, SR)")
    parser.add_argument("--start", type=int, default=1996)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()

    if args.all_countries:
        countries = await tracked_country_iso3s()
    elif args.country:
        countries = [args.country]
    else:
        countries = ["CHE"]

    if args.all_indicators:
        indicators = list(WGI_BASE_INDICATORS)
    elif args.indicator:
        if args.indicator not in WGI_BASE_INDICATORS:
            parser.error(
                f"unknown --indicator {args.indicator!r}; choose one of "
                f"{', '.join(WGI_BASE_INDICATORS)} or --all-indicators"
            )
        indicators = [args.indicator]
    else:
        indicators = list(WGI_BASE_INDICATORS)

    if args.kind:
        kinds = {IndicatorDiagnosticKind(args.kind)}
    else:
        # Default (and --all-kinds): a diagnostic set is imported whole —
        # LB, UB, and SR together.
        kinds = set(IndicatorDiagnosticKind)

    specs = [
        spec
        for spec in WGI_DIAGNOSTIC_SPECS
        if spec.base_indicator_code in indicators and spec.diagnostic_kind in kinds
    ]

    span = f"{args.start}-{args.end or 'now'}"
    print(f"WGI diagnostic batch import: {len(countries)} countries x "
          f"{len(specs)} diagnostic series (source id 3) · {span}\n")

    totals = {"attempted": 0, "succeeded": 0, "failed": 0,
              "received": 0, "inserted": 0, "skipped": 0, "revised": 0}
    failures: list[str] = []

    async with WorldBankWgiDiagnosticFetcher() as fetcher:
        retry_fetcher = TransientRetryFetcher(fetcher)
        for country in countries:
            for spec in specs:
                totals["attempted"] += 1
                result = await import_one(retry_fetcher, country, spec,
                                          args.start, args.end)
                r, i, s, v = result["counts"]
                totals["received"] += r
                totals["inserted"] += i
                totals["skipped"] += s
                totals["revised"] += v
                if result["ok"]:
                    totals["succeeded"] += 1
                else:
                    totals["failed"] += 1
                    failures.append(
                        f"{country} / {spec.provider_series_code} — {result['reason']}"
                    )

    print("\nWGI diagnostic batch import")
    print("---------------------------")
    print(f"Countries: {len(countries)}")
    print(f"Diagnostic series attempted: {totals['attempted']}")
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