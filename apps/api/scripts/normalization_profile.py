"""READ-ONLY descriptive-statistics profile for non-WGI normalization research.

Sprint 5.9 (Part 11) research support for the level-methodology audit
(.dev/NORMALIZATION.md, "Non-WGI Level Parameter Decision Audit"). Prints
per-country and pooled distribution summaries (count, earliest/latest period,
min / p10 / p25 / median / p75 / p90 / max) for the audited indicators.

This script is RESEARCH SUPPORT ONLY. It must NOT:
- produce a level_score or any other score,
- propose or imply a force score,
- write to the DB (SELECT only),
- become an API endpoint,
- be treated as proof that an empirical percentile is economic truth.

Descriptive statistics describe the current sample; they do not justify a
curve. Example (from apps/api):

    uv run --no-sync python scripts/normalization_profile.py
    uv run --no-sync python scripts/normalization_profile.py --indicator GINI_INDEX
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
from app.models import Country, Indicator, Observation

AUDITED_INDICATORS = (
    "GINI_INDEX",
    "GROSS_CAPITAL_FORMATION_GDP",
    "GDP_GROWTH",
    "INFLATION_CPI",
    "UNIT_LABOUR_COST_GROWTH",
    "CREDIT_TO_GDP_GAP",
    "DEBT_SERVICE_RATIO",
    "LABOUR_PRODUCTIVITY_PER_HOUR",
)


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Linear-interpolation percentile on an already-sorted list."""
    if len(sorted_values) == 1:
        return sorted_values[0]
    cut = statistics.quantiles(sorted_values, n=100, method="inclusive")
    return cut[round(pct) - 1]


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4g}"


def _describe(values: list[tuple[str, float]]) -> str | None:
    """Distribution summary lines for [(period_label, value), ...]."""
    if not values:
        return None
    nums = sorted(v for _, v in values)
    periods = [p for p, _ in values]
    lines = [
        f"    observations: {len(nums)}",
        f"    earliest period: {min(periods)}   latest period: {max(periods)}",
        f"    min: {_fmt(nums[0])}   p10: {_fmt(_percentile(nums, 10))}   "
        f"p25: {_fmt(_percentile(nums, 25))}   median: {_fmt(statistics.median(nums))}   "
        f"p75: {_fmt(_percentile(nums, 75))}   p90: {_fmt(_percentile(nums, 90))}   "
        f"max: {_fmt(nums[-1])}",
    ]
    return "\n".join(lines)


def _period_label(period_start: datetime | None) -> str:
    if period_start is None:
        return "?"
    return period_start.date().isoformat()


async def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--indicator",
        action="append",
        help="canonical indicator code (repeatable); default = the 8 audited indicators",
    )
    args = parser.parse_args()
    codes = tuple(c.upper() for c in args.indicator) if args.indicator else AUDITED_INDICATORS

    print("READ-ONLY descriptive profile (Sprint 5.9 research support).")
    print("Descriptive statistics only: NO level_score, NO force score, NO writes,")
    print("NO claim that an empirical percentile is economic truth.")
    print()

    async with get_sessionmaker()() as session:
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
                .where(Indicator.code.in_(codes))
                .order_by(Country.iso3, Observation.period_start)
            )
        ).all()

    # Latest vintage per (indicator, country, period) — the same identity the
    # alignment layer treats as superseded; older vintages are dropped from
    # the profile so revisions do not double-count.
    series: dict[tuple[str, str], dict[datetime | None, tuple[int, float]]] = {}
    for code, iso3, period_start, value, vintage in rows:
        key = (code, iso3)
        series.setdefault(key, {})
        slot = series[key].get(period_start)
        if slot is None or vintage > slot[0]:
            series[key][period_start] = (vintage, value)

    by_indicator: dict[str, dict[str, list[tuple[str, float]]]] = {}
    for (code, iso3), periods in series.items():
        by_indicator.setdefault(code, {})[iso3] = [
            (_period_label(p), v) for p, (_, v) in sorted(periods.items(), key=lambda kv: kv[0])
        ]

    for code in codes:
        print(f"== {code} ==")
        countries = by_indicator.get(code, {})
        if not countries:
            print("    no observations found")
            print()
            continue
        pooled: list[tuple[str, float]] = []
        for iso3 in sorted(countries):
            summary = _describe(countries[iso3])
            print(f"  {iso3}:")
            print(summary)
            pooled.extend(countries[iso3])
        print("  POOLED (all countries):")
        print(_describe(pooled))
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))