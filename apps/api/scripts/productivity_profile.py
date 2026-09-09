"""READ-ONLY research profile for LABOUR_PRODUCTIVITY_PER_HOUR and GDP_GROWTH.

Sprint 6.5 / DEC-033 methodology audit support. Descriptive statistics only —
no scores, no writes, not an API, NOT proof that an empirical percentile is
economic truth.

Usage:
    cd apps/api
    uv run --no-sync python scripts/productivity_profile.py
"""
import asyncio
import sys
import statistics

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select
from app.db.session import get_engine
from app.models import Observation, Country, Indicator
from sqlalchemy.ext.asyncio import AsyncSession

TRACKED_8 = ("USA", "CHE", "DEU", "FRA", "GBR", "JPN", "CHN", "IND")


async def main() -> None:
    engine = get_engine()
    async with AsyncSession(engine) as session:
        for code in ("LABOUR_PRODUCTIVITY_PER_HOUR", "GDP_GROWTH"):
            indicator = (
                await session.execute(
                    select(Indicator).where(Indicator.code == code)
                )
            ).scalar_one()
            print(f"\n=== {code} (id={indicator.id}) ===")
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
                            Observation.indicator_id == indicator.id,
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
                    f"min={min(vals):.2f} p25={p25:.2f} median={med:.2f} "
                    f"p75={p75:.2f} max={max(vals):.2f} latest_val={vals[-1]:.2f}"
                )
                all_vals.extend(vals)
            if all_vals:
                vs = sorted(all_vals)
                n = len(vs)
                print(
                    f"  Pooled: n={n} min={vs[0]:.2f} "
                    f"p25={vs[int(n * 0.25)]:.2f} "
                    f"median={statistics.median(vs):.2f} "
                    f"p75={vs[int(n * 0.75)]:.2f} max={vs[-1]:.2f}"
                )


if __name__ == "__main__":
    asyncio.run(main())
