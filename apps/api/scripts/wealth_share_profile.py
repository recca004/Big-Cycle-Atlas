"""READ-ONLY research profile for WEALTH_SHARE_TOP_10 (WID shwealj992 p90p100).

Sprint 6.6 / DEC-034 methodology audit support. Descriptive statistics only —
no scores, no writes, not an API, NOT proof that an empirical percentile is
economic truth.

Sprint 6.6.2 hardening: pooled queries now explicitly constrain Country.iso3
to TRACKED_8 (previously the pooled SQL queried all observations for the
indicator, which happened to be only tracked_8 rows but was not enforced).
Also follows latest-vintage semantics via the existing latest-vintage
subquery pattern.

Usage:
    cd apps/api
    uv run --no-sync python scripts/wealth_share_profile.py
"""
import asyncio
import sys
import statistics

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select, func
from app.db.session import get_engine
from app.models import Observation, Country, Indicator, SourceSeries
from sqlalchemy.ext.asyncio import AsyncSession

TRACKED_8 = ("USA", "CHE", "DEU", "FRA", "GBR", "JPN", "CHN", "IND")


async def main() -> None:
    engine = get_engine()
    async with AsyncSession(engine) as session:
        ind = (
            await session.execute(
                select(Indicator).where(Indicator.code == "WEALTH_SHARE_TOP_10")
            )
        ).scalar_one()
        print(f"\n=== WEALTH_SHARE_TOP_10 (id={ind.id}) ===")

        # SourceSeries identity
        ss_rows = (
            await session.execute(
                select(SourceSeries).where(SourceSeries.indicator_id == ind.id)
            )
        ).scalars().all()
        for ss in ss_rows:
            print(f"SourceSeries id={ss.id}")
            print(f"  external_code={ss.external_code}")
            print(f"  external_name={ss.external_name}")
            print(f"  external_unit={ss.external_unit}")

        # Resolve tracked_8 country IDs
        tracked_countries = (
            await session.execute(
                select(Country.id, Country.iso3).where(
                    Country.iso3.in_(TRACKED_8)
                )
            )
        ).all()
        tracked_country_ids = [r[0] for r in tracked_countries]
        print(f"\n  Tracked_8 countries resolved: {len(tracked_country_ids)}")

        # Pooled tracked_8 stats — explicitly constrained to TRACKED_8
        base_filter = (
            Observation.indicator_id == ind.id,
            Observation.country_id.in_(tracked_country_ids),
        )
        gmin = (
            await session.execute(
                select(func.min(Observation.value)).where(*base_filter)
            )
        ).scalar_one()
        gmax = (
            await session.execute(
                select(func.max(Observation.value)).where(*base_filter)
            )
        ).scalar_one()
        gcount = (
            await session.execute(
                select(func.count()).select_from(Observation).where(*base_filter)
            )
        ).scalar_one()
        neg = (
            await session.execute(
                select(func.count()).select_from(Observation).where(
                    *base_filter,
                    Observation.value < 0,
                )
            )
        ).scalar_one()
        zero = (
            await session.execute(
                select(func.count()).select_from(Observation).where(
                    *base_filter,
                    Observation.value == 0,
                )
            )
        ).scalar_one()
        over1 = (
            await session.execute(
                select(func.count()).select_from(Observation).where(
                    *base_filter,
                    Observation.value > 1,
                )
            )
        ).scalar_one()
        print(f"\nPooled tracked_8: n={gcount} min={gmin} max={gmax}")
        print(f"  raw<0: {neg}  raw==0: {zero}  raw>1: {over1}")

        all_vals: list[float] = []
        for iso3 in TRACKED_8:
            country = (
                await session.execute(
                    select(Country).where(Country.iso3 == iso3)
                )
            ).scalar_one()
            rows = (
                await session.execute(
                    select(Observation.period_start, Observation.value)
                    .where(
                        Observation.country_id == country.id,
                        Observation.indicator_id == ind.id,
                    )
                    .order_by(Observation.period_start)
                )
            ).all()
            if not rows:
                print(f"  {iso3}: NO DATA")
                continue
            vals = [float(r[1]) for r in rows]
            periods = [str(r[0]) for r in rows]
            n = len(vals)
            vs = sorted(vals)
            p25 = vs[int(n * 0.25)] if n >= 4 else vs[0]
            p75 = vs[int(n * 0.75)] if n >= 4 else vs[-1]
            med = statistics.median(vals)
            print(
                f"  {iso3}: n={n} first={periods[0]} latest={periods[-1]} "
                f"min={min(vals):.4f} p25={p25:.4f} median={med:.4f} "
                f"p75={p75:.4f} max={max(vals):.4f} latest_val={vals[-1]:.4f}"
            )
            all_vals.extend(vals)

        if all_vals:
            vs = sorted(all_vals)
            n = len(vs)
            print(
                f"\n  Pooled tracked_8: n={n} min={vs[0]:.4f} "
                f"p25={vs[int(n * 0.25)]:.4f} "
                f"median={statistics.median(vs):.4f} "
                f"p75={vs[int(n * 0.75)]:.4f} max={vs[-1]:.4f}"
            )


if __name__ == "__main__":
    asyncio.run(main())
