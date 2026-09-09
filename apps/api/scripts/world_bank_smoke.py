"""Manual smoke test: live World Bank fetch, CHE / GDP_GROWTH.

Without --persist: fetch and print only — no database writes (original behavior).

With --persist: after the fetch, persists the DTOs via
observation_service.persist_observations against the normal project DB
configuration (DATABASE_URL). The caller owns the transaction: commit only
after persistence succeeds, rollback on failure. No IngestionRun yet.
"""
import asyncio
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data_sources.base import DataSourceError
from app.data_sources.world_bank import WorldBankAdapter
from app.data_sources.world_bank_mappings import get_world_bank_mapping
from app.db.session import get_sessionmaker
from app.services.observation_service import persist_observations

COUNTRY_ISO3 = "CHE"
INDICATOR_CODE = "GDP_GROWTH"
START_YEAR = 2015


async def main(persist: bool) -> int:
    mapping = get_world_bank_mapping(INDICATOR_CODE)
    if mapping is None:
        print(f"No World Bank mapping for indicator '{INDICATOR_CODE}'.")
        return 1

    print("World Bank live import" if persist else "World Bank live smoke test")
    print("--------------------------")
    print(f"Country: {COUNTRY_ISO3}")
    print(f"Indicator: {INDICATOR_CODE}")
    print(f"External series: {mapping.external_code}")
    print(f"Years: {START_YEAR}–{date.today().year - 1}")
    print()

    async with WorldBankAdapter() as adapter:
        try:
            observations = await adapter.fetch_indicator(
                COUNTRY_ISO3, mapping.external_code, start_year=START_YEAR
            )
        except DataSourceError as exc:
            kind = (
                "World Bank request failed"
                if type(exc).__name__ == "DataSourceHTTPError"
                else "World Bank response could not be parsed"
            )
            print(f"{kind}: {exc}")
            return 1

    for obs in observations:
        print(f"{obs.period}    {obs.value:g}")

    print()
    if observations:
        latest = max(observations, key=lambda o: o.period)
        print(f"Returned: {len(observations)} observations")
        print(f"Latest year: {latest.period} ({latest.value:g} {mapping.external_unit})")
        print(f"Retrieved at: {latest.retrieved_at.isoformat()}")
    else:
        print("Returned: 0 observations")

    if not persist:
        return 0

    print()
    print("Persisting via persist_observations (caller owns the transaction)...")
    session = get_sessionmaker()()
    try:
        result = await persist_observations(session, observations)
        await session.commit()
    except Exception as exc:
        await session.rollback()
        print(f"Database commit: FAILED — {type(exc).__name__}: {exc}")
        return 1
    finally:
        await session.close()

    print()
    print(f"Received: {result.received}")
    print(f"Inserted: {result.inserted}")
    print(f"Skipped: {result.skipped}")
    print(f"Conflicts: {result.conflicts}")
    print()
    print("Database commit: success")
    return 0


if __name__ == "__main__":
    persist_flag = "--persist" in sys.argv[1:]
    sys.exit(asyncio.run(main(persist_flag)))