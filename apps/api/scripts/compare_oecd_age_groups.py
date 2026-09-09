"""Sprint 5.20 Part A1: Compare OECD tertiary attainment Y25T34 vs Y25T64.

Read-only live verification. Queries the official OECD SDMX REST API for
both age groups across all 8 tracked countries and reports coverage stats.

Usage (from apps/api):
    $env:PYTHONPATH='.'; uv run --no-sync python scripts/compare_oecd_age_groups.py
"""
import asyncio
import csv
import io
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx

BASE = "https://sdmx.oecd.org/public/rest"
DATAFLOW = "DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA"
AGENCY = "OECD.EDU.IMEP"
TRACKED_8 = ["USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND"]


async def query_age_group(client: httpx.AsyncClient, ref_area: str, age: str) -> dict:
    # 17 dimensions: REF_AREA.SEX.AGE.ATTAINMENT_LEV + 12 wildcards + FREQ
    key = f"{ref_area}._T.{age}.ISCED11A_5T8." + ".".join(["+"] * 12) + ".A"
    url = f"{BASE}/data/{AGENCY},{DATAFLOW},1.0/{key}?format=csvfilewithlabels"

    try:
        r = await client.get(url)
    except Exception as exc:
        return {"error": str(exc), "count": 0}

    if r.status_code == 404 and "NoRecordsFound" in r.text:
        return {"count": 0, "years": [], "first": None, "latest": None, "no_data": True}

    if r.status_code != 200:
        return {"error": f"HTTP {r.status_code}", "count": 0}

    text = r.text
    if not text.strip():
        return {"count": 0, "years": [], "first": None, "latest": None, "no_data": True}

    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    years_vals = []
    for row in rows:
        y = row.get("TIME_PERIOD", "")
        v = row.get("OBS_VALUE", "")
        if y and v:
            try:
                years_vals.append((int(y), float(v)))
            except ValueError:
                pass

    years_vals.sort()
    years = [y for y, _ in years_vals]
    recent = [y for y in years if y >= 2016]

    return {
        "count": len(years),
        "years": years,
        "first": years[0] if years else None,
        "latest": years[-1] if years else None,
        "recent_10": len(recent),
        "latest_value": years_vals[-1][1] if years_vals else None,
    }


async def main():
    async with httpx.AsyncClient(timeout=120) as client:
        print("=" * 80)
        print("OECD Tertiary Attainment: Y25T34 vs Y25T64 comparison")
        print(f"Dataflow: {DATAFLOW} (agency {AGENCY}, v1.0)")
        print(f"SEX=_T, ATTAINMENT_LEV=ISCED11A_5T8, FREQ=A")
        print("=" * 80)

        for age_label in ["Y25T34", "Y25T64"]:
            print(f"\n--- AGE = {age_label} ---")
            print(f"{'Country':<6} {'Count':>5} {'First':>6} {'Latest':>7} {'Recent10':>9} {'LatestVal':>10}")
            print("-" * 50)
            for iso3 in TRACKED_8:
                result = await query_age_group(client, iso3, age_label)
                if result.get("no_data"):
                    print(f"{iso3:<6} {'NO DATA':>5}")
                elif result.get("error"):
                    print(f"{iso3:<6} ERROR: {result['error']}")
                else:
                    lv = result.get("latest_value")
                    lv_str = f"{lv:.2f}" if lv is not None else "N/A"
                    print(
                        f"{iso3:<6} {result['count']:>5} {result['first']:>6} "
                        f"{result['latest']:>7} {result['recent_10']:>9} {lv_str:>10}"
                    )
                await asyncio.sleep(2.0)  # throttle (60 queries/hour limit)

        print("\n" + "=" * 80)
        print("Comparison complete.")


if __name__ == "__main__":
    asyncio.run(main())
