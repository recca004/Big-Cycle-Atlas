"""Sprint 6.12 read-only research profile: Trade and Capital Flows force audit.

Profiles the tracked_8 empirical data for:
- EXPORTS_GDP
- IMPORTS_GDP
- TRADE_BALANCE
- CURRENT_ACCOUNT_GDP
- derived TRADE_OPENNESS_GDP (computed on demand)

Descriptive ONLY — no scores, no curves, no writes. Used to answer the
Sprint 6.12 methodology questions about whether a defensible LEVEL
exists for the Trade and Capital Flows force.

Usage:
    uv run --no-sync python scripts/_sprint_6_12_trade_capital_profile.py
"""
import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select

from app.cycle.normalization_definitions import ScoringPeriod
from app.db.session import get_sessionmaker
from app.models import Country, Indicator, Observation, SourceSeries
from app.services.derived_indicator_service import derive_trade_openness_as_of

TRACKED_8 = ("USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND")

INDICATORS = (
    "EXPORTS_GDP",
    "IMPORTS_GDP",
    "TRADE_BALANCE",
    "CURRENT_ACCOUNT_GDP",
)


async def profile_indicator(iso3: str, indicator_code: str) -> dict:
    sm = get_sessionmaker()
    async with sm() as session:
        country = (
            await session.execute(select(Country).where(Country.iso3 == iso3))
        ).scalar_one()
        indicator = (
            await session.execute(
                select(Indicator).where(Indicator.code == indicator_code)
            )
        ).scalar_one_or_none()
        if indicator is None:
            return {"indicator": indicator_code, "n": 0, "note": "not in DB"}

        obs = (
            await session.execute(
                select(Observation)
                .where(
                    Observation.country_id == country.id,
                    Observation.indicator_id == indicator.id,
                )
                .order_by(Observation.period_start.asc())
            )
        ).scalars().all()

        if not obs:
            return {"indicator": indicator_code, "n": 0}

        values = [o.value for o in obs]
        years = [o.period_start.year for o in obs]
        return {
            "indicator": indicator_code,
            "n": len(obs),
            "earliest": min(years),
            "latest": max(years),
            "min": min(values),
            "max": max(values),
            "latest_value": values[-1],
            "latest_year": years[-1],
        }


async def profile_derived(iso3: str, scoring_period: ScoringPeriod) -> dict:
    sm = get_sessionmaker()
    async with sm() as session:
        result = await derive_trade_openness_as_of(session, iso3, scoring_period)
        if result.derived_value is None:
            return {"derived": None, "reason": "missing or mismatched"}
        return {
            "derived": result.derived_value,
            "formula_id": result.formula_id,
            "formula_version": result.formula_version,
            "components": [
                {
                    "indicator": c.indicator_code,
                    "source_period": c.aligned_value.source_period if c.aligned_value else None,
                    "raw_value": c.aligned_value.raw_value if c.aligned_value else None,
                    "vintage": c.aligned_value.vintage_number if c.aligned_value else None,
                    "present": c.aligned_value is not None,
                }
                for c in result.components
            ],
        }


async def main():
    sp = ScoringPeriod(2025, 4)

    print("=" * 80)
    print("Sprint 6.12: Trade and Capital Flows — tracked_8 empirical profile")
    print(f"Scoring period: {sp.label}")
    print("=" * 80)

    for iso3 in TRACKED_8:
        print(f"\n--- {iso3} ---")
        for indicator in INDICATORS:
            prof = await profile_indicator(iso3, indicator)
            if prof.get("n", 0) == 0:
                print(f"  {indicator}: no data")
                continue
            print(
                f"  {indicator}: n={prof['n']}, "
                f"{prof['earliest']}-{prof['latest']}, "
                f"min={prof['min']:.2f}, max={prof['max']:.2f}, "
                f"latest={prof['latest_value']:.2f} ({prof['latest_year']})"
            )

        # Derived trade openness
        derived = await profile_derived(iso3, sp)
        if derived.get("derived") is None:
            print(f"  TRADE_OPENNESS_GDP (derived): None ({derived.get('reason')})")
        else:
            print(f"  TRADE_OPENNESS_GDP (derived): {derived['derived']:.2f}")
            for comp in derived["components"]:
                sp_label = comp.get("source_period", "?")
                val = comp.get("raw_value", "?")
                print(f"    {comp['indicator']}: {val} (period={sp_label})")

    print("\n" + "=" * 80)
    print("Descriptive ONLY — no scores, no curves, no writes.")
    print("tracked_8 is NOT global; it is a fixed reference set.")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
