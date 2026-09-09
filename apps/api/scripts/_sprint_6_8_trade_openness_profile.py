"""Sprint 6.8 research: trade-openness derived-indicator empirical profile.

READ-ONLY: no writes, no scores, no persistence. Reports for the tracked-8
countries using real source observations:
- observation overlap n
- first common year
- latest common year
- latest exports % GDP
- latest imports % GDP
- candidate sum (exports + imports)
- min / median / max of the candidate sum

Also reports countries with sum > 100.

Does NOT call tracked_8 "global" or "world."
"""
import asyncio
import json
import selectors
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from app.db import session as session_module
from app.models import Country, Observation, Indicator

TRACKED_8 = ["USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND"]


async def main() -> None:
    sessionmaker = session_module.get_sessionmaker()

    async with sessionmaker() as session:
        # Get country IDs for tracked-8
        country_rows = (
            await session.execute(
                select(Country.iso3, Country.id).where(Country.iso3.in_(TRACKED_8))
            )
        ).all()
        iso3_to_id = {row[0]: row[1] for row in country_rows}

        # Get indicator IDs for EXPORTS_GDP and IMPORTS_GDP
        indicator_rows = (
            await session.execute(
                select(Indicator.id, Indicator.code).where(
                    Indicator.code.in_(["EXPORTS_GDP", "IMPORTS_GDP"])
                )
            )
        ).all()
        code_to_ind_id = {row[1]: row[0] for row in indicator_rows}

        # Get all EXPORTS_GDP and IMPORTS_GDP observations for tracked-8
        obs_rows = (
            await session.execute(
                select(
                    Observation.country_id,
                    Observation.indicator_id,
                    Observation.period_start,
                    Observation.value,
                ).where(
                    Observation.country_id.in_(iso3_to_id.values()),
                    Observation.indicator_id.in_(code_to_ind_id.values()),
                )
            )
        ).all()

    # Organize by country and indicator
    data: dict[str, dict[str, dict[int, float]]] = defaultdict(lambda: defaultdict(dict))
    for country_id, ind_id, period_start, value in obs_rows:
        iso3 = next(k for k, v in iso3_to_id.items() if v == country_id)
        ind_code = next(k for k, v in code_to_ind_id.items() if v == ind_id)
        # period_start is a datetime; extract year
        year = period_start.year if hasattr(period_start, 'year') else int(str(period_start)[:4])
        data[iso3][ind_code][year] = float(value)

    print(f"{'='*80}")
    print(f"  Sprint 6.8 — Trade-Openness Derived-Indicator Empirical Profile")
    print(f"  Tracked-8 countries, read-only, live DB")
    print(f"{'='*80}")

    all_sums: list[float] = []
    all_latest_sums: list[float] = []

    for iso3 in TRACKED_8:
        exports = data[iso3].get("EXPORTS_GDP", {})
        imports = data[iso3].get("IMPORTS_GDP", {})

        exp_years = set(exports.keys())
        imp_years = set(imports.keys())
        common_years = sorted(exp_years & imp_years)

        print(f"\n  {iso3}")
        print(f"    EXPORTS_GDP: {len(exp_years)} obs, years {min(exp_years) if exp_years else '-'}–{max(exp_years) if exp_years else '-'}")
        print(f"    IMPORTS_GDP: {len(imp_years)} obs, years {min(imp_years) if imp_years else '-'}–{max(imp_years) if imp_years else '-'}")
        print(f"    Common years: {len(common_years)}, first={common_years[0] if common_years else '-'}, latest={common_years[-1] if common_years else '-'}")

        if not common_years:
            print(f"    NO overlap — derivation impossible")
            continue

        latest_year = common_years[-1]
        latest_exp = exports[latest_year]
        latest_imp = imports[latest_year]
        latest_sum = latest_exp + latest_imp

        # Compute sums for all common years
        sums = [exports[y] + imports[y] for y in common_years]
        all_sums.extend(sums)
        all_latest_sums.append(latest_sum)

        print(f"    Latest common year ({latest_year}):")
        print(f"      exports = {latest_exp:.2f}%")
        print(f"      imports = {latest_imp:.2f}%")
        print(f"      sum     = {latest_sum:.2f}%")
        print(f"    Sum statistics (all common years, n={len(sums)}):")
        print(f"      min    = {min(sums):.2f}%")
        print(f"      median = {statistics.median(sums):.2f}%")
        print(f"      max    = {max(sums):.2f}%")
        if latest_sum > 100:
            print(f"      *** LATEST SUM > 100 ***")
        if max(sums) > 100:
            print(f"      *** MAX SUM > 100 ({max(sums):.2f}%) ***")

    print(f"\n{'='*80}")
    print(f"  Pooled summary (all common-year sums across tracked-8):")
    print(f"    n      = {len(all_sums)}")
    print(f"    min    = {min(all_sums):.2f}%")
    print(f"    median = {statistics.median(all_sums):.2f}%")
    print(f"    max    = {max(all_sums):.2f}%")
    print(f"    > 100  = {sum(1 for s in all_sums if s > 100)}")

    print(f"\n  Latest-year sums across tracked-8:")
    print(f"    n      = {len(all_latest_sums)}")
    print(f"    min    = {min(all_latest_sums):.2f}%")
    print(f"    median = {statistics.median(all_latest_sums):.2f}%")
    print(f"    max    = {max(all_latest_sums):.2f}%")
    print(f"    > 100  = {sum(1 for s in all_latest_sums if s > 100)}")

    print(f"\n  No writes, no scores, no persistence.")


if __name__ == "__main__":
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
