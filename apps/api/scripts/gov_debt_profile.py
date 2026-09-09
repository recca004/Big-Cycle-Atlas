"""READ-ONLY descriptive-statistics profile for GOVERNMENT_DEBT_GDP
normalization research (Sprint 6.2).

Research support for the government-debt normalization methodology audit
(.dev/NORMALIZATION.md Sprint 6.2 / DEC-031). Prints:

1. Per-country distribution summary (count, earliest/latest period,
   min / p25 / median / p75 / max, current/latest value) for tracked_8.
2. Selected historical snapshot cross-sections (2005, 2010, 2015, 2020,
   latest period-complete year).
3. DEC-019-style own-history counterfactual mid-rank stress score for
   selected countries (JPN, CHE, USA, CHN, FRA) — RESEARCH ONLY, never
   published as a NormalizedSignal.

This script is RESEARCH SUPPORT ONLY. It must NOT:
- produce a published level_score or any other score,
- propose or imply a force score,
- write to the DB (SELECT only),
- become an API endpoint,
- be treated as proof that an empirical percentile is economic truth,
- persist any artifact.

Descriptive statistics describe the current sample; they do not justify a
curve. The own-history counterfactual is diagnostic research, not
validation by intuition.

Usage (from apps/api):

    uv run --no-sync python scripts/gov_debt_profile.py
"""
import asyncio
import statistics
import sys
from datetime import datetime

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, ".")

from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models import Country, Indicator, Observation, SourceSeries
from sqlalchemy import func as sa_func

TRACKED_8 = ("USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND")
COUNTERFACTUAL_COUNTRIES = ("JPN", "CHE", "USA", "CHN", "FRA")
SNAPSHOT_YEARS = (2005, 2010, 2015, 2020)


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


def own_history_mid_rank(sample: list[float], current: float) -> tuple[float, float]:
    """DEC-019-style empirical mid-rank plotting position (RESEARCH ONLY).

    stress_percentile = 100 * (average_rank - 0.5) / n
    rank 1 = lowest value = least stress, ties = average rank.
    Returns (average_rank, stress_percentile). Pure function, no DB access.
    """
    n = len(sample)
    if n == 0:
        raise ValueError("non-empty sample required")
    strictly_below = sum(1 for v in sample if v < current)
    tied = sum(1 for v in sample if v == current)
    if tied == 0:
        raise ValueError("current value not in sample")
    average_rank = strictly_below + (tied + 1) / 2.0
    stress_percentile = 100.0 * (average_rank - 0.5) / n
    return average_rank, stress_percentile


async def main() -> int:
    print("=" * 72)
    print("READ-ONLY GOVERNMENT_DEBT_GDP profile (Sprint 6.2 research support).")
    print("Descriptive statistics + own-history counterfactual ONLY:")
    print("NO published level_score, NO force score, NO writes,")
    print("NO claim that an empirical percentile is economic truth.")
    print("=" * 72)
    print()

    async with get_sessionmaker()() as session:
        # Source-identity guard (Sprint 6.3 Part 0): assert EXACTLY one
        # eligible SourceSeries for GOVERNMENT_DEBT_GDP so a future
        # provider series is never silently merged by canonical indicator.
        series_count = await session.scalar(
            select(sa_func.count())
            .select_from(SourceSeries)
            .join(Indicator, SourceSeries.indicator_id == Indicator.id)
            .where(Indicator.code == "GOVERNMENT_DEBT_GDP")
        )
        if series_count != 1:
            raise SystemExit(
                f"SOURCE-IDENTITY GUARD: expected exactly 1 SourceSeries for "
                f"GOVERNMENT_DEBT_GDP, found {series_count}. Refusing to merge "
                f"multiple provider series by canonical indicator."
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
                .where(Indicator.code == "GOVERNMENT_DEBT_GDP")
                .order_by(Country.iso3, Observation.period_start)
            )
        ).all()

    # Latest vintage per (country, period) — same identity the alignment
    # layer treats as superseded; older vintages dropped so revisions do
    # not double-count.
    series: dict[str, dict[datetime | None, tuple[int, float]]] = {}
    for code, iso3, period_start, value, vintage in rows:
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

    # --- Part 5: per-country profile ---
    print("=" * 72)
    print("PART 5 — Per-country empirical profile (tracked_8, latest vintage)")
    print("=" * 72)
    print()
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

    # --- Part 5b: historical snapshot cross-sections ---
    print("=" * 72)
    print("PART 5b — Historical snapshot cross-sections (as-of, no future)")
    print("=" * 72)
    print()
    for year in SNAPSHOT_YEARS:
        snapshot: list[tuple[str, float]] = []
        for iso3 in TRACKED_8:
            vals = by_country.get(iso3, [])
            # as-of: latest value with period_start year <= snapshot year
            eligible = [(p, v) for p, v in vals if _period_year(p) <= year]
            if eligible:
                snapshot.append((iso3, eligible[-1][1]))
        if snapshot:
            nums = sorted(v for _, v in snapshot)
            print(
                f"  {year}: n={len(snapshot)} "
                f"min={_fmt(nums[0])} median={_fmt(statistics.median(nums))} "
                f"max={_fmt(nums[-1])}"
            )
            for iso3, v in sorted(snapshot, key=lambda kv: kv[1]):
                print(f"    {iso3}: {_fmt(v)}")
        else:
            print(f"  {year}: no eligible observations")
        print()

    # Latest period-complete year cross-section
    all_years = sorted({_period_year(p) for vals in by_country.values() for p, _ in vals})
    if all_years:
        latest_year = all_years[-1]
        snapshot: list[tuple[str, float]] = []
        for iso3 in TRACKED_8:
            vals = by_country.get(iso3, [])
            eligible = [(p, v) for p, v in vals if _period_year(p) <= latest_year]
            if eligible:
                snapshot.append((iso3, eligible[-1][1]))
        if snapshot:
            nums = sorted(v for _, v in snapshot)
            print(
                f"  LATEST period-complete year ({latest_year}): n={len(snapshot)} "
                f"min={_fmt(nums[0])} median={_fmt(statistics.median(nums))} "
                f"max={_fmt(nums[-1])}"
            )
            for iso3, v in sorted(snapshot, key=lambda kv: kv[1]):
                print(f"    {iso3}: {_fmt(v)}")
        print()

    # --- Part 6: own-history counterfactuals ---
    print("=" * 72)
    print("PART 6 — DEC-019-style own-history counterfactual (RESEARCH ONLY)")
    print("Hypothetical mid-rank stress score — NOT a published NormalizedSignal.")
    print("stress_percentile = 100 * (avg_rank - 0.5) / n; level = 100 - stress")
    print("Higher debt/GDP = more stress = WEAKER (same inversion as DSR DEC-019).")
    print("Question: does the ranking look like absolute stock-burden, or merely")
    print("a country's position relative to its own past?")
    print("=" * 72)
    print()
    for iso3 in COUNTERFACTUAL_COUNTRIES:
        vals = by_country.get(iso3, [])
        if not vals:
            print(f"  {iso3}: no observations")
            print()
            continue
        sample = [v for _, v in vals]
        current = sample[-1]
        period = vals[-1][0]
        n = len(sample)
        avg_rank, stress_pct = own_history_mid_rank(sample, current)
        level = 100.0 - stress_pct
        print(f"  {iso3} (n={n}, latest period {period}):")
        print(f"    raw debt/GDP: {_fmt(current)}")
        print(f"    own-history rank: {avg_rank:.2f} / {n}")
        print(f"    hypothetical stress_percentile: {_fmt(stress_pct)}")
        print(f"    hypothetical own-history level: {_fmt(level)}")
        # Show the distribution range for context
        nums = sorted(sample)
        print(
            f"    own-history range: min={_fmt(nums[0])} "
            f"median={_fmt(statistics.median(nums))} max={_fmt(nums[-1])}"
        )
        print()

    print("=" * 72)
    print("END — descriptive research only. No score published. No writes.")
    print("=" * 72)
    return 0


def _period_year(period_label: str) -> int:
    """Extract the year from a YYYY-MM-DD or YYYY period label."""
    try:
        return int(period_label[:4])
    except (ValueError, IndexError):
        return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
