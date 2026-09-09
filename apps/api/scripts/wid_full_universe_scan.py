"""READ-ONLY full-universe scan of WID shwealj992 / p90p100.

Sprint 6.6.1 Part 2 — complete broader WID scan. Scans the entire WID bulk
archive for the EXACT series (variable=shwealj992, percentile=p90p100).
Reports the full empirical domain and identifies any values outside [0,1].

Sprint 6.6.2 fix: the latest-year cross-section now uses the GLOBAL latest
year (max of all entity years), not each entity's own latest year.

NO ingestion. NO DB writes. NO filtering. NO scores.
"""
import csv
import io
import statistics
import zipfile

ARCHIVE = r"C:\Users\mario\AppData\Local\Temp\wid_all_data.zip"
TARGET_VARIABLE = "shwealj992"
TARGET_PERCENTILE = "p90p100"


def main() -> None:
    zf = zipfile.ZipFile(ARCHIVE, "r")

    # Load country metadata to identify sovereign economies vs regions
    countries_raw = zf.read("WID_countries.csv").decode("utf-8")
    countries_reader = csv.DictReader(io.StringIO(countries_raw), delimiter=";")
    # alpha2 -> (shortname, region, region2)
    country_meta: dict[str, tuple[str, str, str]] = {}
    for r in countries_reader:
        country_meta[r["alpha2"]] = (r["shortname"], r["region"], r["region2"])

    # Data file names (exclude metadata, countries csv, region files)
    data_files = [
        n for n in zf.namelist()
        if n.startswith("WID_data_") and n.endswith(".csv")
    ]
    print(f"Data files to scan: {len(data_files)}")

    all_values: list[float] = []
    all_obs: list[tuple[str, int, float]] = []  # (alpha2, year, value)
    entity_counts: dict[str, int] = {}
    entity_ranges: dict[str, tuple[int, int]] = {}  # alpha2 -> (first_year, latest_year)
    out_of_range: list[tuple[str, int, float]] = []
    exactly_one: list[tuple[str, int, float]] = []
    exactly_zero: list[tuple[str, int, float]] = []

    for fname in data_files:
        # Extract alpha2 from filename: WID_data_XX.csv
        alpha2 = fname.replace("WID_data_", "").replace(".csv", "")
        raw = zf.read(fname).decode("utf-8")
        reader = csv.DictReader(io.StringIO(raw), delimiter=";")
        if not reader.fieldnames:
            continue
        required = {"country", "variable", "percentile", "year", "value"}
        if not required.issubset(set(reader.fieldnames)):
            continue

        entity_obs: list[tuple[int, float]] = []
        for row in reader:
            if row is None:
                continue
            if (row.get("variable") or "").strip() != TARGET_VARIABLE:
                continue
            if (row.get("percentile") or "").strip() != TARGET_PERCENTILE:
                continue
            raw_val = (row.get("value") or "").strip()
            if raw_val == "":
                continue
            try:
                val = float(raw_val)
            except ValueError:
                continue
            raw_year = (row.get("year") or "").strip()
            if not raw_year:
                continue
            try:
                year = int(raw_year)
            except ValueError:
                continue
            entity_obs.append((year, val))
            all_obs.append((alpha2, year, val))
            all_values.append(val)
            if val < 0.0 or val > 1.0:
                out_of_range.append((alpha2, year, val))
            if val == 1.0:
                exactly_one.append((alpha2, year, val))
            if val == 0.0:
                exactly_zero.append((alpha2, year, val))

        if entity_obs:
            entity_counts[alpha2] = len(entity_obs)
            years = [y for y, _ in entity_obs]
            entity_ranges[alpha2] = (min(years), max(years))

    zf.close()

    # Compute the GLOBAL latest year across ALL observations
    all_years_list = [y for _, y, _ in all_obs]
    global_latest_year = max(all_years_list) if all_years_list else 0

    # Latest-year cross-section: only observations where year == global_latest_year
    latest_year_values = [
        (alpha2, val) for alpha2, year, val in all_obs
        if year == global_latest_year
    ]

    # Report
    print(f"\n=== FULL UNIVERSE SCAN: {TARGET_VARIABLE} / {TARGET_PERCENTILE} ===")
    print(f"WID archive entities with exact series: {len(entity_counts)}")
    print(f"Total observations: {len(all_values)}")

    if all_values:
        vs = sorted(all_values)
        n = len(vs)
        all_years = [y for _, (f, l) in entity_ranges.items() for y in (f, l)]
        print(f"Year range: {min(all_years)} – {max(all_years)}")
        print(f"Min: {vs[0]:.6f}")
        print(f"p01: {vs[int(n * 0.01)]:.6f}")
        print(f"p05: {vs[int(n * 0.05)]:.6f}")
        print(f"p25: {vs[int(n * 0.25)]:.6f}")
        print(f"Median: {statistics.median(vs):.6f}")
        print(f"p75: {vs[int(n * 0.75)]:.6f}")
        print(f"p95: {vs[int(n * 0.95)]:.6f}")
        print(f"p99: {vs[int(n * 0.99)]:.6f}")
        print(f"Max: {vs[-1]:.6f}")
        neg_count = sum(1 for v in all_values if v < 0)
        zero_count = sum(1 for v in all_values if v == 0)
        over1_count = sum(1 for v in all_values if v > 1)
        one_count = sum(1 for v in all_values if v == 1)
        print(f"Count raw < 0: {neg_count}")
        print(f"Count raw == 0: {zero_count}")
        print(f"Count raw > 1: {over1_count}")
        print(f"Count raw == 1: {one_count}")

    print(f"\nGlobal latest year: {global_latest_year}")
    if latest_year_values:
        lvs = [v for _, v in latest_year_values]
        print(f"Same-year cross-section n (year={global_latest_year}): {len(lvs)}")
        print(f"Same-year min: {min(lvs):.6f}")
        print(f"Same-year max: {max(lvs):.6f}")

    if out_of_range:
        print(f"\n=== VALUES OUTSIDE [0,1] ({len(out_of_range)} found) ===")
        for alpha2, year, val in out_of_range[:50]:
            meta = country_meta.get(alpha2, ("?", "?", "?"))
            print(f"  {alpha2} ({meta[0]}) year={year} value={val:.6f}")
        if len(out_of_range) > 50:
            print(f"  ... and {len(out_of_range) - 50} more")
    else:
        print("\n=== NO VALUES OUTSIDE [0,1] FOUND ===")

    if exactly_one:
        print(f"\n=== VALUES EXACTLY == 1.0 ({len(exactly_one)} found) ===")
        for alpha2, year, val in exactly_one[:20]:
            meta = country_meta.get(alpha2, ("?", "?", "?"))
            print(f"  {alpha2} ({meta[0]}) year={year} value={val:.6f}")

    if exactly_zero:
        print(f"\n=== VALUES EXACTLY == 0.0 ({len(exactly_zero)} found) ===")
        for alpha2, year, val in exactly_zero[:20]:
            meta = country_meta.get(alpha2, ("?", "?", "?"))
            print(f"  {alpha2} ({meta[0]}) year={year} value={val:.6f}")

    # Identify which entities are sovereign vs region
    print(f"\n=== ENTITY CLASSIFICATION ===")
    sovereign = 0
    region_entities = 0
    unknown = 0
    for alpha2 in entity_counts:
        meta = country_meta.get(alpha2)
        if meta is None:
            unknown += 1
        elif meta[1] == "World" or alpha2.startswith("X") or alpha2.startswith("Q"):
            region_entities += 1
        else:
            sovereign += 1
    print(f"Sovereign economies (approx): {sovereign}")
    print(f"Region/aggregate entities (approx): {region_entities}")
    print(f"Unknown: {unknown}")


if __name__ == "__main__":
    main()

