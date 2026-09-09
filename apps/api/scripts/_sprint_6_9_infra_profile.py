"""Sprint 6.9 research: Infrastructure & Investment proxy candidate profiles.

READ-ONLY: fetches WB API data for three candidate indicators across
tracked-8 and the broader real-economy universe. No writes, no scores.

Candidates:
1. LP.LPI.OVRL.XQ  — LPI Overall score (1=low to 5=high)
2. LP.LPI.INFR.XQ  — LPI Quality of trade/transport infrastructure (1-5)
3. EG.ELC.ACCS.ZS — Access to electricity (% of population)
4. IT.NET.USER.ZS — Individuals using Internet (% of population)
"""
import json
import statistics
import urllib.request

TRACKED_8 = ["USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND"]

CANDIDATES = [
    ("LP.LPI.OVRL.XQ", "LPI Overall score (1=low to 5=high)"),
    ("LP.LPI.INFR.XQ", "LPI Infrastructure quality (1=low to 5=high)"),
    ("EG.ELC.ACCS.ZS", "Access to electricity (% of population)"),
    ("IT.NET.USER.ZS", "Individuals using Internet (% of population)"),
]

COUNTRY_URL = "https://api.worldbank.org/v2/country/all?format=json&per_page=500"


def fetch_json(url: str) -> list:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    # Get country metadata to filter aggregates
    country_data = fetch_json(COUNTRY_URL)
    aggregate_iso3 = set()
    all_country_names = {}
    for c in country_data[1]:
        iso3 = c.get("iso3Code") or ""
        name = c.get("name") or ""
        region = c.get("region") or {}
        region_id = region.get("id") if isinstance(region, dict) else None
        all_country_names[iso3] = name
        if region_id is None or region_id == "NA":
            aggregate_iso3.add(iso3)

    print(f"{'='*80}")
    print(f"  Sprint 6.9 — Infrastructure & Investment Proxy Candidate Profiles")
    print(f"{'='*80}")

    for code, label in CANDIDATES:
        url = (
            f"https://api.worldbank.org/v2/country/all/indicator/{code}"
            f"?format=json&per_page=20000&date=2000:2025"
        )
        data = fetch_json(url)

        if not data or len(data) < 2 or data[1] is None:
            print(f"\n  {code} ({label}): NO DATA")
            continue

        obs = data[1]

        # Organize by country
        by_country: dict[str, dict[str, float]] = {}
        for o in obs:
            iso3 = o.get("countryiso3code") or ""
            year = o.get("date") or ""
            value = o.get("value")
            if value is not None and iso3 and iso3 not in aggregate_iso3:
                by_country.setdefault(iso3, {})[year] = float(value)

        print(f"\n{'='*80}")
        print(f"  {code} — {label}")
        print(f"  Real economies with data: {len(by_country)}")
        print(f"{'='*80}")

        # Tracked-8 profile
        print(f"\n  Tracked-8 profile:")
        for iso3 in TRACKED_8:
            years_data = by_country.get(iso3, {})
            if not years_data:
                print(f"    {iso3}: NO DATA")
                continue
            years_sorted = sorted(years_data.keys())
            values = [years_data[y] for y in years_sorted]
            latest_year = years_sorted[-1]
            latest_val = years_data[latest_year]
            print(
                f"    {iso3}: n={len(values)}, first={years_sorted[0]}, "
                f"latest={latest_year} ({latest_val:.2f}), "
                f"min={min(values):.2f}, median={statistics.median(values):.2f}, "
                f"max={max(values):.2f}"
            )

        # Broader universe profile (latest available year per country)
        latest_values = []
        for iso3, years_data in by_country.items():
            if iso3 in aggregate_iso3:
                continue
            years_sorted = sorted(years_data.keys())
            latest_values.append(years_data[years_sorted[-1]])

        if latest_values:
            latest_sorted = sorted(latest_values)
            n = len(latest_sorted)
            print(f"\n  Broader real-economy profile (latest available year per economy, n={n}):")
            print(f"    min    = {latest_sorted[0]:.2f}")
            print(f"    p25    = {latest_sorted[n // 4]:.2f}")
            print(f"    median = {statistics.median(latest_sorted):.2f}")
            print(f"    p75    = {latest_sorted[3 * n // 4]:.2f}")
            print(f"    p90    = {latest_sorted[int(n * 0.9)]:.2f}")
            print(f"    p95    = {latest_sorted[int(n * 0.95)]:.2f}")
            print(f"    max    = {latest_sorted[-1]:.2f}")

            # Check saturation for percentage indicators
            if "%" in label:
                near_100 = sum(1 for v in latest_values if v >= 95)
                at_100 = sum(1 for v in latest_values if v >= 99)
                print(f"    >= 95% = {near_100} ({100 * near_100 / n:.1f}%)")
                print(f"    >= 99% = {at_100} ({100 * at_100 / n:.1f}%)")

            # Top and bottom 5
            sorted_countries = sorted(
                by_country.items(),
                key=lambda x: x[1][max(x[1].keys())] if x[1] else 0,
                reverse=True,
            )
            print(f"\n  Top 5:")
            for iso3, years_data in sorted_countries[:5]:
                if iso3 in aggregate_iso3:
                    continue
                latest_y = max(years_data.keys())
                name = all_country_names.get(iso3, iso3)
                print(f"    {iso3} ({name}): {years_data[latest_y]:.2f} ({latest_y})")

            print(f"  Bottom 5:")
            for iso3, years_data in sorted_countries[-5:]:
                if iso3 in aggregate_iso3:
                    continue
                latest_y = max(years_data.keys())
                name = all_country_names.get(iso3, iso3)
                print(f"    {iso3} ({name}): {years_data[latest_y]:.2f} ({latest_y})")

    print(f"\n  No writes, no scores, no persistence.")


if __name__ == "__main__":
    main()
