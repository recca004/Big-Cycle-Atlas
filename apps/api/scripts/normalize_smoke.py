"""Read-only smoke check for the normalization path (Sprints 5.6-5.12).

Examples (from apps/api):

    uv run --no-sync python scripts/normalize_smoke.py \
        --country CHE --indicator RULE_OF_LAW_WGI_SCORE --period 2025-Q2

    uv run --no-sync python scripts/normalize_smoke.py \
        --all-tracked --indicator DEBT_SERVICE_RATIO --period 2025-Q4

Uses the live DB for SELECT queries only — nothing is written. Exits 0 with a
signal report, 1 with a clear reason (no eligible observation, too stale,
unsupported family, unknown codes).
"""
import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, ".")

from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    NormalizationFamily,
    TRACKED_8_MEMBERS,
)
from app.cycle.normalizer import (
    NormalizationDataError,
    NormalizationNotImplementedError,
    normalize_indicator_as_of,
)
from app.db.session import get_sessionmaker
from app.services.alignment_service import AlignmentError, parse_scoring_period

WGI_INDICATORS = (
    "RULE_OF_LAW_WGI_SCORE",
    "CONTROL_OF_CORRUPTION_WGI_SCORE",
    "POLITICAL_STABILITY_WGI_SCORE",
)


def _print_signal(signal) -> None:
    print(f"Country: {signal.country_iso3}")
    print(f"Indicator: {signal.indicator_code}")
    print(f"Scoring period: {signal.as_of_period.label}")
    print(f"Source observation: {signal.source_period}")
    print(f"Raw value: {signal.raw_value:g}")
    if signal.method is NormalizationFamily.own_history:
        oh = signal.own_history_level
        if oh is not None and oh.level_score is not None:
            print(f"Level score: {oh.level_score:g}  (OWN_HISTORY empirical mid-rank - "
                  "position in the country's OWN expanding history, NOT a "
                  "cross-country comparison, NOT a force score)")
        else:
            print(f"Level score: not available (own-history sample {oh.sample_n} < "
                  f"required {oh.minimum_sample_n}) - NOT zero, never stretched")
        if oh is not None:
            print(f"Own-history sample n: {oh.sample_n}  (minimum {oh.minimum_sample_n})")
            print(f"Calibration span: {oh.earliest_source_period} through "
                  f"{oh.latest_source_period}  (expanding own history - actual "
                  "observations only, never forward-filled)")
            rank = f"{oh.rank:g}" if oh.rank is not None else "n/a"
            stress = f"{oh.stress_percentile:g}" if oh.stress_percentile is not None else "n/a"
            print(f"Historical rank: {rank}   Stress percentile: {stress}"
                  "  (level = 100 - stress percentile)")
    elif signal.method is NormalizationFamily.one_sided_vulnerability:
        osv = signal.one_sided_vulnerability_level
        print(f"Level score: {signal.level_score:.2f}  (ONE_SIDED_VULNERABILITY - "
              "owner-approved curve, DEC-021; indicator-level signal, NOT a "
              "force score)")
        if osv is not None:
            print(f"Curve: {osv.no_excess_score:g} at or below +{osv.neutral_ceiling:g}pp "
                  f"(neutral - absence of excess credit is NOT evidence of strength), "
                  f"linear to {osv.saturated_score:g} at +{osv.saturation_value:g}pp, "
                  f"clamped at {osv.saturated_score:g} above (Atlas MODEL PARAMETERS - "
                  "breakpoints coincide with the Basel CCyB guide L/H, score "
                  "mapping is an Atlas choice)")
    else:
        print(f"Level score: {signal.level_score:g}  (DIRECT_0_100 - provider's "
              "absolute scale, indicator-level signal, NOT a force score)")
    if signal.momentum_windows:
        print("Momentum (OWN_HISTORY - signed change in provider's own 0-100 points, "
              "NOT calibrated for cross-indicator aggregation):")
        if signal.momentum is not None:
            print(f"  Primary window: {signal.momentum_window_years} years")
            print(f"  Momentum: {signal.momentum:+g}  (primary window only - no averaging, no fallback)")
        else:
            print("  Momentum: not available (primary window missing or outside anchor "
                  "tolerance) - NOT zero, no fallback to another window")
        for result in signal.momentum_windows:
            anchor = result.anchor_source_period or "none (no alignable observation)"
            change = f"{result.change:+g}" if result.change is not None else "None"
            print(f"  {result.window_years}y window: requested anchor "
                  f"{result.requested_anchor_period}, actual source anchor {anchor}, "
                  f"change {change}")
    else:
        print("Momentum: not calculated")
    if signal.reference_universe_id is not None:
        expected_n = signal.reference_universe_expected_n or 0
        usable_n = signal.reference_universe_usable_n or 0
        if signal.relative_score is not None and signal.relative_rank is not None:
            print(f"Relative score: {signal.relative_score:g}")
        else:
            print("Relative score: not available")
        print(f"Reference universe: {signal.reference_universe_id}")
        if signal.relative_score is not None and signal.relative_rank is not None:
            print(f"Relative rank: {signal.relative_rank:g} / {expected_n}")
        print(f"Universe usable: {usable_n} / {expected_n}")
        print("  (relative position within tracked_8 - NOT a global/world percentile)")
    else:
        print("Relative score: not calculated")
    print("Confidence: not calculated")
    print(f"Freshness factor: {signal.freshness_factor:.4f}" + ("  (stale)" if signal.is_stale else "")
          + "  (applies to the CURRENT observation only - historical anchors and "
          "calibration points are never decayed)")
    print(f"Backtest safe: {str(signal.backtest_safe).lower()}")
    print(f"Model version: {signal.model_version}")
    if signal.indicator_code in WGI_INDICATORS:
        print("Note: WGI is a perception-based composite with measurement uncertainty "
              "(CI/SE series documented, not imported).")
    if signal.indicator_code == "DEBT_SERVICE_RATIO":
        print("Note: cross-country raw-DSR ranking is prohibited (BIS caution) - "
              "relative score stays not-calculated by design.")
    if signal.indicator_code == "CREDIT_TO_GDP_GAP":
        print("Note: the gap is a common reference point, NOT a mechanical "
              "standalone rule (Basel caution, DEC-020) - GDP-denominator "
              "distortions, trend turning points, and post-bust artifacts "
              "limit score interpretation. Relative stays deferred; momentum "
              "windows (4q/8q) stay unapproved.")


async def _load_signal(session, country: str, indicator: str, scoring_period):
    return await normalize_indicator_as_of(
        session,
        country_iso3=country.upper(),
        indicator_code=indicator.upper(),
        scoring_period=scoring_period,
        model_config=CURRENT_MODEL_VERSION,
    )


async def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all-tracked",
        action="store_true",
        help="loop over every tracked_8 country instead of --country",
    )
    parser.add_argument("--country", help="ISO3 code, e.g. CHE")
    parser.add_argument("--indicator", required=True, help="canonical indicator code")
    parser.add_argument("--period", required=True, help="scoring period, e.g. 2025-Q2")
    args = parser.parse_args()

    if not args.all_tracked and not args.country:
        parser.error("either --country or --all-tracked is required")

    try:
        scoring_period = parse_scoring_period(args.period)
    except AlignmentError as exc:
        print(f"ERROR: {exc}")
        return 1

    countries = TRACKED_8_MEMBERS if args.all_tracked else (args.country,)
    failures = 0
    async with get_sessionmaker()() as session:
        for country in countries:
            if args.all_tracked:
                print(f"=== {country} ===")
            try:
                signal = await _load_signal(
                    session, country, args.indicator, scoring_period
                )
            except (
                NormalizationNotImplementedError,
                NormalizationDataError,
                AlignmentError,
                ValueError,
            ) as exc:
                print(f"ERROR: {exc}")
                failures += 1
                continue
            if signal is None:
                print("No normalized signal: no period-complete latest-vintage observation "
                      "at or before the scoring period, or the aligned observation is too "
                      "stale for the freshness policy. Nothing was zero-filled.")
                failures += 1
                continue
            _print_signal(signal)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))