"""Market data import (Mission 5 §18).

Seeds the verified instrument registry, then fetches each instrument's
FRED series and persists observations idempotently — re-runs only insert
new dates, never overwrite stored values.

    python scripts/ingest_markets.py                    # all instruments
    python scripts/ingest_markets.py --code DGS10       # one external code
    python scripts/ingest_markets.py --code US_SP500 --start 2010-01-01
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.data_sources.fred import FredAdapter  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_engine, get_sessionmaker  # noqa: E402
from app.market import service as market_service  # noqa: E402
from app.models import MarketInstrument  # noqa: E402  (registers models)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default=None,
                    help="instrument code or FRED external code")
    ap.add_argument("--start", default=None, help="YYYY-MM-DD")
    ap.add_argument("--end", default=None, help="YYYY-MM-DD")
    args = ap.parse_args()

    start = date.fromisoformat(args.start) if args.start else None
    end = date.fromisoformat(args.end) if args.end else None

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sm = get_sessionmaker()
    async with sm() as session:
        res = await market_service.seed_instruments(session)
        await session.commit()
        print(f"instruments seeded: {res}")

    async with sm() as session:
        q = select(MarketInstrument).where(MarketInstrument.active)
        if args.code:
            q = q.where(
                (MarketInstrument.code == args.code)
                | (MarketInstrument.external_code == args.code)
            )
        instruments = list((await session.execute(q)).scalars())
    if not instruments:
        print("no matching instruments")
        return 1

    failures = 0
    async with FredAdapter() as adapter:
        for inst in instruments:
            async with sm() as session:
                outcome = await market_service.run_market_ingestion(
                    session, adapter, inst, start=start, end=end
                )
                await session.commit()
            status = outcome["status"]
            print(f"{inst.code:28s} [{inst.external_code}] -> {status} "
                  f"inserted={outcome.get('inserted', '-')}")
            if status == "failed":
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
