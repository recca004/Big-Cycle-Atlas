"""Track C: WID wealth-share exact-series coverage audit (v2).

Download the WID bulk zip, extract only the 8 tracked country files,
and audit shweal p90p100 / p99p100 coverage.
"""
import asyncio
import sys
import io
import zipfile
import os
import tempfile
import csv

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import httpx

WID_COUNTRIES = {
    "USA": "US",
    "CHN": "CN",
    "CHE": "CH",
    "DEU": "DE",
    "FRA": "FR",
    "GBR": "GB",
    "JPN": "JP",
    "IND": "IN",
}

TARGET_PERCENTILES = {"p90p100", "p99p100"}
BULK_URL = "https://wid.world/bulk_download/wid_all_data.zip"
CACHE_PATH = os.path.join(tempfile.gettempdir(), "wid_bulk.zip")


async def download_bulk():
    """Download the WID bulk zip to a temp file if not already cached."""
    if os.path.exists(CACHE_PATH) and os.path.getsize(CACHE_PATH) > 100_000_000:
        print(f"  Using cached {CACHE_PATH} ({os.path.getsize(CACHE_PATH)} bytes)")
        return
    print(f"  Downloading from {BULK_URL}...")
    async with httpx.AsyncClient(timeout=300) as c:
        with open(CACHE_PATH, "wb") as f:
            async with c.stream("GET", BULK_URL, follow_redirects=True) as r:
                r.raise_for_status()
                total = 0
                async for chunk in r.aiter_bytes(chunk_size=1024 * 1024):
                    f.write(chunk)
                    total += len(chunk)
                    if total % (50 * 1024 * 1024) < 1024 * 1024:
                        print(f"    {total / (1024*1024):.0f} MB...")
        print(f"  Downloaded {os.path.getsize(CACHE_PATH)} bytes")


def audit_country(zf: zipfile.ZipFile, iso2: str, iso3: str):
    """Audit shweal p90p100/p99p100 for one country."""
    filename = f"WID_data_{iso2}.csv"
    try:
        with zf.open(filename) as f:
            text = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
            reader = csv.DictReader(text, delimiter=";")
            rows = list(reader)
    except KeyError:
        print(f"  {iso3} ({iso2}): FILE NOT FOUND in zip")
        return

    # Filter for shweal with target percentiles
    # Variable column includes age suffix: shwealj992, shwealj999, etc.
    shweal_rows = [r for r in rows if r.get("variable", "").startswith("shweal")]
    target_rows = [r for r in shweal_rows if r.get("percentile") in TARGET_PERCENTILES]

    if not target_rows:
        print(f"  {iso3} ({iso2}): NO shweal p90p100/p99p100 data")
        return

    # Group by percentile and age/pop
    from collections import defaultdict
    groups = defaultdict(list)
    for r in target_rows:
        key = (r["percentile"], r["variable"], r["age"], r["pop"])
        groups[key].append(r)

    print(f"\n  {iso3} ({iso2}):")
    for (pctile, var, age, pop), grp in sorted(groups.items()):
        years = sorted(int(r["year"]) for r in grp)
        values = {int(r["year"]): r["value"] for r in grp}
        print(f"    {pctile} var={var} age={age} pop={pop}: {len(years)} obs, {years[0]}–{years[-1]}")

        # Check for gaps (missing years)
        all_years = set(range(years[0], years[-1] + 1))
        missing = sorted(all_years - set(years))
        if missing:
            print(f"      Missing years ({len(missing)}): {missing[:20]}{'...' if len(missing) > 20 else ''}")
        else:
            print(f"      No gaps (complete {years[0]}–{years[-1]})")

        # Check for extrapolations: data_quality column or constant values
        # WID data_quality: 0 = raw, 1 = interpolated, 2 = extrapolated (typical)
        dq_counts = defaultdict(int)
        for r in grp:
            dq_counts[r.get("data_quality", "?")] += 1
        print(f"      data_quality: {dict(dq_counts)}")

        # Show sample values at key years
        for y in [1980, 1990, 2000, 2010, 2020, years[-1]]:
            if y in values:
                print(f"        {y}: {values[y]}")

    # Also check what age/pop combinations exist for shweal
    age_pops = set()
    for r in shweal_rows:
        age_pops.add((r.get("variable", ""), r.get("age", ""), r.get("pop", "")))
    if len(age_pops) > 1:
        print(f"    All shweal variable/age/pop combos: {sorted(age_pops)}")


def main():
    print("=== Track C: WID wealth-share exact-series coverage audit (v2) ===\n")
    asyncio.run(download_bulk())

    print("\n--- Auditing tracked_8 countries ---")
    with zipfile.ZipFile(CACHE_PATH, "r") as zf:
        for iso3, iso2 in WID_COUNTRIES.items():
            audit_country(zf, iso2, iso3)

    # Clean up
    print(f"\n  Cache file: {CACHE_PATH}")


if __name__ == "__main__":
    main()
