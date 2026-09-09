"""Live OECD smoke test: fetch labour productivity for one tracked country.

Read-only against the official OECD SDMX API — no database writes, no
Indicator/SourceSeries rows. Run from apps/api:
    uv run --no-sync python scripts/oecd_smoke.py [CHE|USA]
"""
import asyncio
import sys

from app.data_sources.base import DataSourceError
from app.data_sources.oecd import OECDAdapter
from app.data_sources.oecd_mappings import get_oecd_mapping_by_external_code

COUNTRY = sys.argv[1].upper() if len(sys.argv) > 1 else "CHE"
PROD_CODE = "DSD_PDB@DF_PDB/{cc}.A.GDPHRS._T.USD_PPP_H.LR.N._Z.PPP"


async def main() -> None:
    mapping = get_oecd_mapping_by_external_code(PROD_CODE)
    if mapping is None:
        raise SystemExit(f"Unsupported mapping: {PROD_CODE}")

    print("OECD live smoke")
    print(f"Country: {COUNTRY}")
    print(f"Indicator: {mapping.indicator_code} ({mapping.external_name})")
    print(f"Dataset: {mapping.agency_id}/{mapping.dataflow_id} v{mapping.version}")
    print("Frequency: annual")
    print(f"Unit: {mapping.external_unit}")

    adapter = OECDAdapter()
    try:
        observations = await adapter.fetch_indicator(
            COUNTRY, PROD_CODE, start_year=2019, end_year=2025
        )
    except DataSourceError as exc:
        raise SystemExit(f"Live fetch failed: {exc}")
    finally:
        await adapter.aclose()

    observations.sort(key=lambda o: o.observation_date)
    for obs in observations:
        print(f"{obs.period}  {obs.value:.4f}")
    print(f"Observations: {len(observations)}")
    print(f"Latest period: {observations[-1].period}")


if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())