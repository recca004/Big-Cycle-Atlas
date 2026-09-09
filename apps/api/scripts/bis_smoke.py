"""Live BIS smoke test: fetch the credit-to-GDP gap for one tracked country.

Read-only against the BIS Stats API — no database writes. Run from apps/api:
    uv run --no-sync python scripts/bis_smoke.py [CHE|USA]
"""
import asyncio
import sys

from app.data_sources.base import DataSourceError
from app.data_sources.bis import BISAdapter
from app.data_sources.bis_mappings import BIS_ISO2_BY_ISO3, get_bis_mapping_by_external_code

COUNTRY = sys.argv[1].upper() if len(sys.argv) > 1 else "CHE"
GAP_CODE = "WS_CREDIT_GAP/Q.{cc}.P.A.C"


async def main() -> None:
    iso2 = BIS_ISO2_BY_ISO3.get(COUNTRY)
    mapping = get_bis_mapping_by_external_code(GAP_CODE)
    if iso2 is None or mapping is None:
        raise SystemExit(f"Unsupported country or mapping: {COUNTRY}")

    print("BIS live smoke")
    print(f"Country: {COUNTRY}")
    print(f"Indicator: {mapping.indicator_code} ({mapping.external_name})")
    print(f"Dataset: {mapping.dataflow_id}")
    print("Frequency: quarterly")
    print(f"Unit: {mapping.external_unit}")

    adapter = BISAdapter()
    try:
        observations = await adapter.fetch_indicator(
            COUNTRY, GAP_CODE, start_year=2024, end_year=2025
        )
    except DataSourceError as exc:
        raise SystemExit(f"Live fetch failed: {exc}")
    finally:
        await adapter.aclose()

    observations.sort(key=lambda o: o.observation_date)
    for obs in observations:
        quarter = (obs.observation_date.month - 1) // 3 + 1
        print(f"{obs.period} Q{quarter}  {obs.value:.4f}")
    latest = observations[-1]
    latest_quarter = (latest.observation_date.month - 1) // 3 + 1
    print(f"Observations: {len(observations)}")
    print(f"Latest period: {latest.period} Q{latest_quarter}")


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())