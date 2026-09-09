"""READ-ONLY descriptive-statistics profile for TERTIARY_ATTAINMENT_25_34
normalization research (Sprint 6.3).

Research support for the Education level calibration + proxy-force
eligibility audit (.dev/NORMALIZATION.md Sprint 6.3 / DEC-032). Prints:

1. Per-country distribution summary (count, earliest/latest period,
   min / p25 / median / p75 / max, current/latest value) for tracked_8
   from the production DB (read-only SELECT).
2. Freshness at a common scoring snapshot (2025-Q2).
3. Broader OECD dataflow universe profile (read-only external SDMX fetch
   with a wildcard REF_AREA dimension) — economy count, year span,
   distribution by sufficiently populated year, latest cross section.
   Distinguishes OECD/dataflow universe from tracked_8 and from
   world/global.

This script is RESEARCH SUPPORT ONLY. It must NOT:
- produce a published level_score or any other score,
- propose or imply a force score,
- write to the DB (SELECT only),
- become an API endpoint,
- be treated as proof that an empirical percentile is economic truth,
- persist any artifact,
- fabricate missing years or interpolate raw observations.

Descriptive statistics describe the current sample; they do not justify a
curve.

Usage (from apps/api):

    uv run --no-sync python scripts/education_profile.py
"""
import asyncio
import csv
import io
import statistics
import sys
from datetime import datetime

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, ".")

import httpx
from sqlalchemy import func as sa_func, select

from app.db.session import get_sessionmaker
from app.models import Country, Indicator, Observation, SourceSeries

TRACKED_8 = ("USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND")
SNAPSHOT_YEAR = 2025  # common scoring snapshot for freshness check

# OECD SDMX endpoint for the education dataflow (read-only external fetch).
OECD_BASE_URL = "https://sdmx.oecd.org/public/rest"
OECD_AGENCY = "OECD.EDU.IMEP"
OECD_DATAFLOW = "DSD_EAG_LSO_EA@DF_LSO_NEAC_DISTR_EA"
OECD_VERSION = "1.0"
# Wildcard REF_AREA (+) to fetch ALL countries in the dataflow. The
# remaining 16 dimensions are fixed exactly as in production
# (oecd_mappings.TERTIARY_ATTAINMENT_25_34).
OECD_WILDCARD_KEY = (
    "+._T.Y25T34.ISCED11A_5T8._T.POP._Z._T._Z."
    "ED_NED.POP._Z.PT_POP_SEX_AGE.OBS._Z.NEAC.A"
)


def _percentile(sorted_values: list[float], pct: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    cut = statistics.quantiles(sorted_values, n=100, method="inclusive")
    return cut[round(pct) - 1]


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4g}"


def _period_label(period_start: datetime | None) -> str:
    if period_start is None:
        return "?"
    return period_start.date().isoformat()


def _period_year(period_label: str) -> int:
    try:
        return int(period_label[:4])
    except (ValueError, IndexError):
        return 0


def _describe(values: list[tuple[str, float]]) -> str | None:
    if not values:
        return None
    nums = sorted(v for _, v in values)
    periods = [p for p, _ in values]
    lines = [
        f"    observations: {len(nums)}",
        f"    earliest period: {min(periods)}   latest period: {max(periods)}",
        f"    min: {_fmt(nums[0])}   p25: {_fmt(_percentile(nums, 25))}   "
        f"median: {_fmt(statistics.median(nums))}   "
        f"p75: {_fmt(_percentile(nums, 75))}   max: {_fmt(nums[-1])}",
        f"    current/latest value: {_fmt(values[-1][1])} "
        f"(period {values[-1][0]})",
    ]
    return "\n".join(lines)


async def _profile_tracked_8() -> None:
    """Profile the production TERTIARY_ATTAINMENT_25_34 series for tracked_8."""
    print("=" * 72)
    print("PART A — Per-country empirical profile (tracked_8, latest vintage)")
    print("Source: production DB (read-only SELECT). No writes.")
    print("=" * 72)
    print()

    async with get_sessionmaker()() as session:
        # Source-identity guard: assert EXACTLY one eligible SourceSeries.
        series_count = await session.scalar(
            select(sa_func.count())
            .select_from(SourceSeries)
            .join(Indicator, SourceSeries.indicator_id == Indicator.id)
            .where(Indicator.code == "TERTIARY_ATTAINMENT_25_34")
        )
        if series_count != 1:
            raise SystemExit(
                f"SOURCE-IDENTITY GUARD: expected exactly 1 SourceSeries for "
                f"TERTIARY_ATTAINMENT_25_34, found {series_count}."
            )
        rows = (
            await session.execute(
                select(
                    Indicator.code,
                    Country.iso3,
                    Observation.period_start,
                    Observation.value,
                    Observation.vintage_number,
                )
                .join(Observation, Observation.indicator_id == Indicator.id)
                .join(Country, Observation.country_id == Country.id)
                .where(Indicator.code == "TERTIARY_ATTAINMENT_25_34")
                .order_by(Country.iso3, Observation.period_start)
            )
        ).all()

    # Latest vintage per (country, period)
    series: dict[str, dict[datetime | None, tuple[int, float]]] = {}
    for _code, iso3, period_start, value, vintage in rows:
        series.setdefault(iso3, {})
        slot = series[iso3].get(period_start)
        if slot is None or vintage > slot[0]:
            series[iso3][period_start] = (vintage, value)

    by_country: dict[str, list[tuple[str, float]]] = {}
    for iso3, periods in series.items():
        by_country[iso3] = [
            (_period_label(p), v)
            for p, (_, v) in sorted(periods.items(), key=lambda kv: kv[0])
        ]

    pooled: list[tuple[str, float]] = []
    for iso3 in TRACKED_8:
        vals = by_country.get(iso3, [])
        print(f"  {iso3}:")
        summary = _describe(vals)
        print(summary if summary else "    no observations found")
        print()
        pooled.extend(vals)

    print("  POOLED (all tracked_8):")
    print(_describe(pooled))
    print()

    # Freshness at a common scoring snapshot (2025-Q2 equivalent: year <= 2025)
    print("=" * 72)
    print(f"PART A2 — Freshness at common scoring snapshot (year <= {SNAPSHOT_YEAR})")
    print("=" * 72)
    print()
    for iso3 in TRACKED_8:
        vals = by_country.get(iso3, [])
        eligible = [(p, v) for p, v in vals if _period_year(p) <= SNAPSHOT_YEAR]
        if eligible:
            latest_p, latest_v = eligible[-1]
            print(f"  {iso3}: latest eligible = {latest_v:.4g} (period {latest_p})")
        else:
            print(f"  {iso3}: NO eligible observation at or before {SNAPSHOT_YEAR}")
    print()

    # Sparsity flag
    print("=" * 72)
    print("PART A3 — Sparsity assessment")
    print("=" * 72)
    print()
    for iso3 in TRACKED_8:
        vals = by_country.get(iso3, [])
        n = len(vals)
        flag = ""
        if n <= 2:
            flag = "  <-- EXTREMELY SPARSE (level/momentum not viable)"
        elif n <= 11:
            flag = "  <-- SPARSE (momentum may be unreliable; level depends on method)"
        else:
            flag = "  <-- adequate for level/momentum candidates"
        print(f"  {iso3}: n={n}{flag}")
    print()


async def _profile_oecd_universe() -> None:
    """Profile the broader OECD dataflow universe (read-only external fetch).

    Uses a wildcard REF_AREA (+) to fetch ALL countries in the dataflow.
    This is a read-only SDMX GET — no DB writes, no ingestion.
    """
    print("=" * 72)
    print("PART B — Broader OECD dataflow universe (read-only external SDMX fetch)")
    print(f"Dataflow: {OECD_AGENCY},{OECD_DATAFLOW},{OECD_VERSION}")
    print("Wildcard REF_AREA (+) = all countries in the dataflow.")
    print("This is the OECD/dataflow universe — NOT tracked_8, NOT world/global.")
    print("=" * 72)
    print()

    url = f"{OECD_BASE_URL}/data/{OECD_AGENCY},{OECD_DATAFLOW},{OECD_VERSION}/{OECD_WILDCARD_KEY}"
    params = {"format": "csvfilewithlabels"}

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url, params=params)
    except httpx.HTTPError as exc:
        print(f"  OECD fetch failed: {exc}")
        print("  (external API unavailable — skipping broader-universe profile)")
        return

    if response.status_code != 200:
        print(f"  OECD returned HTTP {response.status_code}")
        print("  (skipping broader-universe profile)")
        return

    # Parse CSV with labels
    reader = csv.DictReader(io.StringIO(response.text))
    rows = list(reader)
    if not rows:
        print("  No rows returned from OECD dataflow.")
        return

    # Identify the REF_AREA and value columns (OECD CSV with labels uses
    # uppercase dimension names; REF_AREA is the country dimension).
    ref_col = None
    val_col = None
    period_col = None
    for col in reader.fieldnames:
        if col.strip().upper() == "REF_AREA":
            ref_col = col
        if col.strip().upper() == "OBS_VALUE":
            val_col = col
        if col.strip().upper() in ("TIME_PERIOD", "TIME"):
            period_col = col
    if ref_col is None or val_col is None or period_col is None:
        print(f"  Could not identify columns. Fieldnames: {reader.fieldnames}")
        return

    # Build per-country series
    by_country: dict[str, dict[int, float]] = {}
    for row in rows:
        ref = row[ref_col].strip()
        val_str = row[val_col].strip()
        period_str = row[period_col].strip()
        if not val_str:
            continue
        try:
            val = float(val_str)
        except ValueError:
            continue
        try:
            year = int(period_str[:4])
        except ValueError:
            continue
        # Keep latest value per (country, year) — no duplicates
        by_country.setdefault(ref, {})[year] = val

    economy_count = len(by_country)
    all_years = sorted({y for years in by_country.values() for y in years})
    if not all_years:
        print("  No valid observations parsed.")
        return

    print(f"  Economies in dataflow: {economy_count}")
    print(f"  Year span: {all_years[0]}–{all_years[-1]}")
    print()

    # Distribution by sufficiently populated year (n >= 20)
    print("  Distribution by year (n >= 20 economies):")
    for year in all_years:
        n = sum(1 for years in by_country.values() if year in years)
        if n >= 20:
            vals = sorted(years[year] for years in by_country.values() if year in years)
            print(
                f"    {year}: n={n}  min={_fmt(vals[0])}  "
                f"median={_fmt(statistics.median(vals))}  max={_fmt(vals[-1])}"
            )
    print()

    # Latest cross section
    latest_year = all_years[-1]
    vals = sorted(
        years[latest_year] for years in by_country.values() if latest_year in years
    )
    n_latest = len(vals)
    print(f"  Latest year ({latest_year}) cross section: n={n_latest}")
    if vals:
        print(
            f"    min={_fmt(vals[0])}  p25={_fmt(_percentile(vals, 25))}  "
            f"median={_fmt(statistics.median(vals))}  "
            f"p75={_fmt(_percentile(vals, 75))}  max={_fmt(vals[-1])}"
        )
    print()

    # Universe composition changes (count by decade)
    print("  Universe composition by decade (economies with >=1 obs):")
    for decade_start in range(all_years[0] - (all_years[0] % 10), all_years[-1] + 1, 10):
        decade_end = decade_start + 9
        n = sum(
            1
            for years in by_country.values()
            if any(decade_start <= y <= decade_end for y in years)
        )
        if n > 0:
            print(f"    {decade_start}s: {n} economies with >=1 observation")
    print()

    # tracked_8 within the dataflow
    print("  tracked_8 within the dataflow (by REF_AREA presence):")
    # We don't have an ISO3->REF_AREA map here, but we can report the
    # total economy count and note that tracked_8 is a subset.
    print(f"    dataflow economies: {economy_count}")
    print(f"    tracked_8: {len(TRACKED_8)} (a frozen subset, NOT the dataflow universe)")
    print("    NOTE: OECD/dataflow universe != world/global. Some non-OECD")
    print("    countries participate in OECD education dataflows; the universe")
    print("    is the dataflow membership, not OECD member states only.")
    print()


async def main() -> int:
    print("=" * 72)
    print("READ-ONLY TERTIARY_ATTAINMENT_25_34 profile (Sprint 6.3 research).")
    print("Descriptive statistics ONLY:")
    print("NO published level_score, NO force score, NO writes,")
    print("NO claim that an empirical percentile is economic truth.")
    print("=" * 72)
    print()

    await _profile_tracked_8()
    await _profile_oecd_universe()

    print("=" * 72)
    print("END — descriptive research only. No score published. No writes.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
