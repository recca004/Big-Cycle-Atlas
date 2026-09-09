"""Sprint 6.8 research: broader WB trade-openness profile.

READ-ONLY: fetches WB API data for EXPORTS_GDP and IMPORTS_GDP across all
real economies, computes the trade-openness sum (exports + imports), and
reports the distribution. Uses WB country metadata to remove aggregates.

No writes, no scores, no persistence.
"""
import json
import statistics
import urllib.request

# WB API: fetch exports and imports for all countries, latest available year
EXPORTS_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/NE.EXP.GNFS.ZS"
    "?format=json&per_page=20000&date=2000:2024"
)
IMPORTS_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/NE.IMP.GNFS.ZS"
    "?format=json&per_page=20000&date=2000:2024"
)
# Country metadata to identify aggregates
COUNTRY_URL = "https://api.worldbank.org/v2/country/all?format=json&per_page=500"


def fetch_json(url: str) -> list:
    with urllib.request.urlopen(url, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    # Get country metadata to filter aggregates
    country_data = fetch_json(COUNTRY_URL)
    # country_data[1] is the list of country objects
    aggregate_iso3 = set()
    all_country_names = {}
    for c in country_data[1]:
        iso3 = c.get("iso3Code") or ""
        name = c.get("name") or ""
        region = c.get("region") or {}
        region_id = region.get("id") if isinstance(region, dict) else None
        all_country_names[iso3] = name
        # Aggregates have region id = "NA" or no region
        if region_id is None or region_id == "NA":
            aggregate_iso3.add(iso3)

    print(f"  Total WB entities: {len(country_data[1])}")
    print(f"  Aggregates identified: {len(aggregate_iso3)}")

    # Fetch exports and imports
    exp_data = fetch_json(EXPORTS_URL)
    imp_data = fetch_json(IMPORTS_URL)

    # Organize by country and year
    exports_by_country: dict[str, dict[str, float]] = {}
    for obs in exp_data[1]:
        iso3 = obs.get("countryiso3code") or ""
        year = obs.get("date") or ""
        value = obs.get("value")
        if value is not None and iso3 and iso3 not in aggregate_iso3:
            exports_by_country.setdefault(iso3, {})[year] = float(value)

    imports_by_country: dict[str, dict[str, float]] = {}
    for obs in imp_data[1]:
        iso3 = obs.get("countryiso3code") or ""
        year = obs.get("date") or ""
        value = obs.get("value")
        if value is not None and iso3 and iso3 not in aggregate_iso3:
            imports_by_country.setdefault(iso3, {})[year] = float(value)

    # Compute trade openness = exports + imports for each country-year pair
    all_sums: list[float] = []
    latest_sums: list[float] = []
    country_latest: dict[str, tuple[int, float, float, float]] = {}

    for iso3 in set(exports_by_country.keys()) & set(imports_by_country.keys()):
        exp_years = exports_by_country[iso3]
        imp_years = imports_by_country[iso3]
        common_years = sorted(set(exp_years.keys()) & set(imp_years.keys()))
        if not common_years:
            continue
        for year in common_years:
            s = exp_years[year] + imp_years[year]
            all_sums.append(s)
        latest_year = int(common_years[-1])
        latest_exp = exp_years[common_years[-1]]
        latest_imp = imp_years[common_years[-1]]
        latest_sum = latest_exp + latest_imp
        latest_sums.append(latest_sum)
        country_latest[iso3] = (latest_year, latest_exp, latest_imp, latest_sum)

    print(f"\n{'='*80}")
    print(f"  Sprint 6.8 — Broader WB Trade-Openness Profile")
    print(f"  Real economies only (aggregates removed)")
    print(f"{'='*80}")

    print(f"\n  Economy count (with both exports + imports): {len(country_latest)}")
    print(f"  Year range: 2000–2024")
    print(f"  Total country-year pairs: {len(all_sums)}")

    if all_sums:
        all_sums_sorted = sorted(all_sums)
        n = len(all_sums_sorted)
        print(f"\n  All country-year sums:")
        print(f"    min    = {all_sums_sorted[0]:.2f}%")
        print(f"    p25    = {all_sums_sorted[n//4]:.2f}%")
        print(f"    median = {statistics.median(all_sums_sorted):.2f}%")
        print(f"    p75    = {all_sums_sorted[3*n//4]:.2f}%")
        print(f"    p90    = {all_sums_sorted[int(n*0.9)]:.2f}%")
        print(f"    p95    = {all_sums_sorted[int(n*0.95)]:.2f}%")
        print(f"    max    = {all_sums_sorted[-1]:.2f}%")
        print(f"    > 100  = {sum(1 for s in all_sums if s > 100)} ({100*sum(1 for s in all_sums if s > 100)/n:.1f}%)")

    if latest_sums:
        latest_sorted = sorted(latest_sums)
        n = len(latest_sorted)
        print(f"\n  Latest-year sums per economy (n={n}):")
        print(f"    min    = {latest_sorted[0]:.2f}%")
        print(f"    p25    = {latest_sorted[n//4]:.2f}%")
        print(f"    median = {statistics.median(latest_sorted):.2f}%")
        print(f"    p75    = {latest_sorted[3*n//4]:.2f}%")
        print(f"    p90    = {latest_sorted[int(n*0.9)]:.2f}%")
        print(f"    p95    = {latest_sorted[int(n*0.95)]:.2f}%")
        print(f"    max    = {latest_sorted[-1]:.2f}%")
        print(f"    > 100  = {sum(1 for s in latest_sums if s > 100)} ({100*sum(1 for s in latest_sums if s > 100)/n:.1f}%)")

    # Top 10 highest latest sums
    print(f"\n  Top 10 highest latest trade-openness sums:")
    sorted_latest = sorted(country_latest.items(), key=lambda x: x[1][3], reverse=True)
    for iso3, (year, exp, imp, s) in sorted_latest[:10]:
        name = all_country_names.get(iso3, iso3)
        print(f"    {iso3} ({name}): {s:.2f}% (exp={exp:.1f}, imp={imp:.1f}, {year})")

    # Bottom 10
    print(f"\n  Bottom 10 lowest latest trade-openness sums:")
    for iso3, (year, exp, imp, s) in sorted_latest[-10:]:
        name = all_country_names.get(iso3, iso3)
        print(f"    {iso3} ({name}): {s:.2f}% (exp={exp:.1f}, imp={imp:.1f}, {year})")

    print(f"\n  No writes, no scores, no persistence.")


if __name__ == "__main__":
    main()
