"""Sprint 6.7 live read-only smoke: WID wealth level + Wealth-gap force at 2025-Q4.

READ-ONLY: no writes, no API, no persistence. Reports for the tracked-8
countries at 2025-Q4:
- raw top-10 wealth share
- normalized wealth level (100 * (1 - raw))
- force level
- coverage

Verifies:
    normalized level == 100 * (1 - raw)
    force level == normalized level
    relative is None
    momentum is None
    confidence is None
    coverage is PARTIAL
"""
import asyncio
import selectors
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.cycle.force_definitions import ForceCoverageStatus
from app.cycle.normalization_definitions import ScoringPeriod
from app.cycle.normalizer import normalize_indicator_as_of
from app.db import session as session_module
from app.services.force_signal_service import build_force_signals_as_of

TRACKED_8 = ["USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND"]


async def main() -> None:
    period = ScoringPeriod(2025, 4)
    sessionmaker = session_module.get_sessionmaker()

    all_ok = True
    for iso3 in TRACKED_8:
        print(f"\n{'='*70}")
        print(f"  {iso3}  -  {period.label}")
        print(f"{'='*70}")

        async with sessionmaker() as session:
            norm = await normalize_indicator_as_of(
                session, iso3, "WEALTH_SHARE_TOP_10", period
            )
            signals = await build_force_signals_as_of(session, iso3, period)

        assert len(signals) == 17, f"expected 17, got {len(signals)}"

        wg = next(s for s in signals if s.force_code == "wealth_opportunity_values_gaps")

        if norm is None:
            print(f"  WEALTH_SHARE_TOP_10: no signal (missing/stale)")
            print(f"  wealth_gap force: level={wg.level_score} coverage={wg.coverage_status.value}")
            print(f"  [smoke: no WID signal for {iso3}]")
            continue

        raw = norm.raw_value
        expected_level = 100.0 * (1.0 - raw)

        print(f"  raw top-10 share:      {raw:.4f}")
        print(f"  normalized level:      {norm.level_score:.4f}")
        print(f"  force level:           {wg.level_score}")
        print(f"  coverage:              {wg.coverage_status.value}")

        # Verify invariants
        checks = [
            ("normalized == 100*(1-raw)", norm.level_score == expected_level),
            ("force == normalized", wg.level_score == norm.level_score),
            ("relative is None", norm.relative_score is None),
            ("momentum is None", norm.momentum is None),
            ("confidence is None", norm.confidence is None),
            ("force relative None", wg.relative_score is None),
            ("force momentum None", wg.momentum is None),
            ("force confidence None", wg.confidence is None),
            ("coverage is PARTIAL", wg.coverage_status is ForceCoverageStatus.partial),
            ("scoring_component == WEALTH_SHARE_TOP_10",
             wg.scoring_component_indicator == "WEALTH_SHARE_TOP_10"),
        ]
        for label, ok in checks:
            status = "OK" if ok else "FAIL"
            if not ok:
                all_ok = False
            print(f"  [{status}] {label}")

        print(f"  [smoke: 17 forces returned, no writes]")

    print(f"\n{'='*70}")
    print(f"  Smoke complete. All checks: {'PASS' if all_ok else 'FAIL'}")
    print(f"  No writes, no API, no persistence.")
    print(f"{'='*70}")


if __name__ == "__main__":
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    finally:
        loop.close()
