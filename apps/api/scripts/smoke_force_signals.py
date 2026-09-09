"""Sprint 5.22 live read-only smoke: build 17 ForceSignals for 2025-Q2.

READ-ONLY: no writes, no API, no persistence. Reports the 3 approved
identity forces + Indebtedness coverage/score for CHE/USA/CHN/IND.
"""
import asyncio
import selectors
import sys
from pathlib import Path

# Add the repository parent to sys.path so `app` is importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cycle.normalization_definitions import ScoringPeriod
from app.db import session as session_module
from app.services.force_signal_service import build_force_signals_as_of


async def main() -> None:
    period = ScoringPeriod(2025, 2)
    countries = ["CHE", "USA", "CHN", "IND"]
    sessionmaker = session_module.get_sessionmaker()

    for iso3 in countries:
        print(f"\n{'='*70}")
        print(f"  {iso3}  -  {period.label}")
        print(f"{'='*70}")
        async with sessionmaker() as session:
            signals = await build_force_signals_as_of(session, iso3, period)

        assert len(signals) == 17, f"expected 17, got {len(signals)}"

        for s in signals:
            if s.force_code in ("rule_of_law", "corruption", "internal_conflict"):
                comp = s.scoring_component_indicator or "-"
                src = "-"
                if s.component_signals:
                    src = s.component_signals[0].source_period
                print(
                    f"  {s.force_code:30s} "
                    f"level={str(s.level_score):>8s}  "
                    f"relative={str(s.relative_score):>8s}  "
                    f"momentum={str(s.momentum):>8s}  "
                    f"coverage={s.coverage_status.value:20s}  "
                    f"src={src}  comp={comp}"
                )
            elif s.force_code == "indebtedness":
                dsr_level = "-"
                cg_level = "-"
                for cs in s.component_signals:
                    if cs.indicator_code == "DEBT_SERVICE_RATIO":
                        dsr_level = cs.level_score
                    elif cs.indicator_code == "CREDIT_TO_GDP_GAP":
                        cg_level = cs.level_score
                print(
                    f"  {s.force_code:30s} "
                    f"level={str(s.level_score):>8s}  "
                    f"coverage={s.coverage_status.value:20s}  "
                    f"DSR={str(dsr_level):>8s}  CreditGap={str(cg_level):>8s}"
                )

        print(f"  [smoke: 17 forces returned, no writes]")

    print("\nSmoke complete. No writes, no API, no persistence.")


if __name__ == "__main__":
    # Windows + psycopg async requires SelectorEventLoop, not ProactorEventLoop.
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
