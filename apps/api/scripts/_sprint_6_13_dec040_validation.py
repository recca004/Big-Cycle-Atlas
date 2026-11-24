"""Sprint 6.13 — DEC-040 indebtedness validation report (READ-ONLY).

Produces .dev/DEC-040_VALIDATION.md: eight-country latest breakdown,
quarterly historical profile (retrospective diagnostics — NOT
release-date-safe backtests; backtest_safe stays False), crisis-period
review, sensitivity analysis of the penalty strength, and the
assumption boundary between inherited approvals and Atlas model choice.

No DB writes. No score is persisted. Run:
    uv run python scripts/_sprint_6_13_dec040_validation.py
"""
import asyncio
import selectors
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from app.cycle.force_aggregation_definitions import (
    FORCE_AGGREGATION_CONFIGS,
    FORCE_AGGREGATION_VERSION,
    ForceIndicatorRole,
)
from app.cycle.force_signal import aggregate_force_from_signals
from app.cycle.normalization_definitions import ScoringPeriod
from app.cycle.normalizer import normalize_indicator_as_of
from app.db import session as session_module
from app.services.force_coverage_service import get_force_coverage

COUNTRIES = ["USA", "CHN", "CHE", "DEU", "FRA", "GBR", "JPN", "IND"]
SPEC = FORCE_AGGREGATION_CONFIGS["indebtedness"]
CORE = "DEBT_SERVICE_RATIO"
PENALTY = "CREDIT_TO_GDP_GAP"
CONTEXT = "GOVERNMENT_DEBT_GDP"

# Quarterly history: data starts 2000-Q1.
PERIODS = [
    ScoringPeriod(y, q)
    for y in range(2000, 2027)
    for q in range(1, 5)
    if (y, q) <= (2026, 3)
]

CRISIS_WINDOWS = {
    "GFC 2008-2009": [ScoringPeriod(y, q) for y in (2008, 2009) for q in range(1, 5)],
    "Eurozone crisis 2010-2013": [ScoringPeriod(y, q) for y in (2010, 2011, 2012, 2013) for q in range(1, 5)],
    "COVID 2020": [ScoringPeriod(2020, q) for q in range(1, 5)],
    "Tightening 2022-2023": [ScoringPeriod(y, q) for y in (2022, 2023) for q in range(1, 5)],
}


def _q_end(p: ScoringPeriod) -> str:
    return p.label


async def build_indebtedness(session, iso3: str, period: ScoringPeriod, coverage):
    """Normalize the indebtedness components and aggregate — no other forces."""
    signals = {}
    for comp in SPEC.components:
        if comp.role is ForceIndicatorRole.supporting_context:
            # CONTEXTUAL_DEFERRED — normalization not implemented; record only.
            signals[comp.indicator_code] = None
            continue
        signals[comp.indicator_code] = await normalize_indicator_as_of(
            session, iso3, comp.indicator_code, period
        )
    fs = aggregate_force_from_signals(
        force_spec=SPEC,
        country_iso3=iso3,
        scoring_period=period.label,
        component_signals=signals,
        coverage_status=coverage.status,
        coverage_ceiling=None,
    )
    return fs, signals


def decompose(fs, signals):
    """Pull the human-readable decomposition out of a ForceSignal."""
    dsr = signals.get(CORE)
    gap = signals.get(PENALTY)
    out = {
        "force_level": fs.level_score,
        "dsr_raw": dsr.raw_value if dsr else None,
        "dsr_source_period": dsr.source_period if dsr else None,
        "dsr_level": dsr.level_score if dsr else None,
        "gap_raw": gap.raw_value if gap else None,
        "gap_source_period": gap.source_period if gap else None,
        "gap_level": gap.level_score if gap else None,
        "penalty": None,
        "dsr_sample_n": None,
        "dsr_min_n": None,
        "dsr_earliest": None,
        "dsr_latest": None,
        "dsr_stress_pct": None,
        "dsr_fresh": dsr.freshness_factor if dsr else None,
        "gap_fresh": gap.freshness_factor if gap else None,
        "dsr_stale": dsr.is_stale if dsr else None,
        "gap_stale": gap.is_stale if gap else None,
        "missing": list(fs.missing_components),
    }
    if dsr and dsr.own_history_level:
        oh = dsr.own_history_level
        out.update(
            dsr_sample_n=oh.sample_n,
            dsr_min_n=oh.minimum_sample_n,
            dsr_earliest=oh.earliest_source_period,
            dsr_latest=oh.latest_source_period,
            dsr_stress_pct=oh.stress_percentile,
        )
    if out["dsr_level"] is not None and out["gap_level"] is not None:
        out["penalty"] = out["gap_level"] - 50.0
    return out


async def main() -> None:
    out_path = (
        Path(__file__).resolve().parents[3] / ".dev" / "DEC-040_VALIDATION.md"
    )
    sessionmaker = session_module.get_sessionmaker()
    lines: list[str] = []
    w = lines.append

    w("# DEC-040 validation report — Indebtedness CONDITION_MINUS_PENALTY")
    w("")
    w(f"Generated: retrospective diagnostic run (NOT release-date-safe;")
    w("backtest_safe = False everywhere). Model: " + FORCE_AGGREGATION_VERSION)
    w("")

    coverage_cache: dict = {}
    history: dict[str, dict[str, dict]] = {}  # iso3 -> period label -> decomp
    latest_gov_debt: dict[str, tuple] = {}

    async with sessionmaker() as session:
        for iso3 in COUNTRIES:
            if iso3 not in coverage_cache:
                cov = await get_force_coverage(session, (await session.execute(
                    text("select id from countries where iso3=:i"), {"i": iso3}
                )).scalar_one())
                coverage_cache[iso3] = next(
                    c for c in cov if c.definition.code == "indebtedness"
                )
            coverage = coverage_cache[iso3]

            # latest gov-debt context (raw, unscored)
            row = (await session.execute(text(
                "select o.value, o.period_start::text from observations o "
                "join indicators i on i.id=o.indicator_id join countries c on c.id=o.country_id "
                "where c.iso3=:i and i.code='GOVERNMENT_DEBT_GDP' "
                "order by o.period_start desc, o.vintage_number desc limit 1"
            ), {"i": iso3})).first()
            latest_gov_debt[iso3] = (row.value, row.period_start) if row else (None, None)

            history[iso3] = {}
            for period in PERIODS:
                fs, signals = await build_indebtedness(
                    session, iso3, period, coverage
                )
                d = decompose(fs, signals)
                # Only keep periods that reached data (avoid storing empties)
                if d["dsr_raw"] is not None or d["gap_raw"] is not None or d["force_level"] is not None:
                    history[iso3][period.label] = d

    # --- Part 1: latest breakdown --------------------------------------
    w("## 1. Latest snapshot per country")
    w("")
    w("| Country | Period | DSR raw | DSR src | cal n | cal span | stress % | DSR level | gap raw | gap src | gap level | penalty | **force level** | coverage |")
    w("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    latest_rows: dict[str, dict] = {}
    for iso3 in COUNTRIES:
        hist = history[iso3]
        scored_periods = [p for p in hist if hist[p]["force_level"] is not None]
        key = scored_periods[-1] if scored_periods else (list(hist)[-1] if hist else None)
        d = hist[key] if key else {}
        latest_rows[iso3] = {**d, "period": key}
        f = lambda v, nd=2: "—" if v is None else f"{v:.{nd}f}"
        w(
            f"| {iso3} | {key} | {f(d.get('dsr_raw'))} | {d.get('dsr_source_period') or '—'} "
            f"| {d.get('dsr_sample_n') or '—'}/{d.get('dsr_min_n') or '—'} "
            f"| {d.get('dsr_earliest') or '—'}…{d.get('dsr_latest') or '—'} "
            f"| {f(d.get('dsr_stress_pct'))} | {f(d.get('dsr_level'))} "
            f"| {f(d.get('gap_raw'))} | {d.get('gap_source_period') or '—'} "
            f"| {f(d.get('gap_level'))} | {f(d.get('penalty'))} "
            f"| **{f(d.get('force_level'))}** | {coverage_cache[iso3].status.value} |"
        )
    w("")
    w("Government-debt context (SUPPORTING_CONTEXT, unscored): "
      + "; ".join(
          f"{iso3} {latest_gov_debt[iso3][0]:.1f}% ({str(latest_gov_debt[iso3][1])[:4]})"
          if latest_gov_debt[iso3][0] is not None else f"{iso3} —"
          for iso3 in COUNTRIES
      ))
    w("")

    # --- Part 2: CHE deep-dive -----------------------------------------
    w("## 2. Switzerland 13.46 — decomposition")
    w("")
    che = latest_rows["CHE"]
    w(f"- DSR raw {che.get('dsr_raw')}: own-history stress percentile "
      f"{che.get('dsr_stress_pct'):.1f} → DSR level {che.get('dsr_level'):.1f} "
      f"(n={che.get('dsr_sample_n')}, span {che.get('dsr_earliest')}…{che.get('dsr_latest')}).")
    w(f"- Credit gap raw {che.get('gap_raw')} → gap level {che.get('gap_level')} "
      f"→ penalty {che.get('penalty')}.")
    w(f"- Force level = clamp({che.get('dsr_level'):.1f} + ({che.get('penalty')}), 0, 100) "
      f"= **{che.get('force_level'):.2f}**.")
    dsr_share = abs(che['penalty']) if che.get('penalty') is not None else None
    w("")
    if che.get("penalty") == 0:
        w("Driver: **entirely the DSR own-history percentile** — the credit gap is neutral.")
    elif che.get("penalty") is not None:
        w(f"Driver: DSR contributes {che.get('dsr_level'):.1f}; the credit-gap "
          f"penalty subtracts {abs(che['penalty']):.1f}. "
          f"{'The score is dominated by the DSR term.' if abs(che['penalty']) < che['dsr_level'] else 'The penalty dominates.'}")
    w("")

    # --- Part 3: crisis windows ----------------------------------------
    w("## 3. Historical profile — crisis windows")
    w("")
    for label, periods in CRISIS_WINDOWS.items():
        w(f"### {label}")
        w("")
        w("| Country | periods scored | min | mean | max | mean DSR | mean penalty |")
        w("|---|---|---|---|---|---|---|")
        for iso3 in COUNTRIES:
            vals, dsr_vals, pen_vals = [], [], []
            for p in periods:
                d = history[iso3].get(p.label)
                if not d:
                    continue
                if d["force_level"] is not None:
                    vals.append(d["force_level"])
                if d["dsr_level"] is not None:
                    dsr_vals.append(d["dsr_level"])
                if d["penalty"] is not None:
                    pen_vals.append(d["penalty"])
            if vals:
                w(
                    f"| {iso3} | {len(vals)}/{len(periods)} | {min(vals):.1f} "
                    f"| {statistics.mean(vals):.1f} | {max(vals):.1f} "
                    f"| {statistics.mean(dsr_vals):.1f} "
                    f"| {statistics.mean(pen_vals):.1f} |"
                )
            else:
                w(f"| {iso3} | 0/{len(periods)} | — | — | — | — | — |")
        w("")

    # --- Part 4: sensitivity -------------------------------------------
    w("## 4. Sensitivity analysis")
    w("")
    all_levels = [d["force_level"] for h in history.values() for d in h.values() if d["force_level"] is not None]
    all_pen = [d["penalty"] for h in history.values() for d in h.values() if d["penalty"] is not None]
    all_dsr = [d["dsr_level"] for h in history.values() for d in h.values() if d["dsr_level"] is not None]
    w(f"- Scored snapshots: {len(all_levels)} of "
      f"{sum(len(h) for h in history.values())} data-bearing snapshots.")
    w(f"- Penalty distribution: min {min(all_pen):.1f}, max {max(all_pen):.1f}, "
      f"mean {statistics.mean(all_pen):.1f}; fraction of scored snapshots with "
      f"penalty < 0 (gap elevated): {sum(1 for p in all_pen if p < -0.01)/len(all_pen):.1%}.")
    w(f"- Zero-level snapshots: {sum(1 for v in all_levels if v <= 0.0)} "
      f"({sum(1 for v in all_levels if v <= 0.0)/len(all_levels):.1%}).")
    w(f"- 100-level snapshots: {sum(1 for v in all_levels if v >= 100.0)}.")
    w(f"- Level range: {min(all_levels):.1f} … {max(all_levels):.1f}; "
      f"DSR-core range: {min(all_dsr):.1f} … {max(all_dsr):.1f}.")
    # compression: correlation between force level and DSR level
    paired = [
        (d["dsr_level"], d["force_level"])
        for h in history.values() for d in h.values()
        if d["force_level"] is not None and d["dsr_level"] is not None
    ]
    xs, ys = zip(*paired)
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((a - mx) * (b - my) for a, b in paired)
    r = cov / (statistics.pstdev(xs) * statistics.pstdev(ys) * len(paired))
    w(f"- Compression: corr(force level, DSR core) = {r:.3f} "
      f"(1.0 = penalty never moves the score).")
    w("")

    w("### Penalty-strength variants (research-only, production formula unchanged)")
    w("")
    w("| strength s | min | mean | max | zero-share |")
    w("|---|---|---|---|---|")
    variant_rows = []
    for s in (0.0, 0.5, 1.0, 1.5, 2.0):
        vals = []
        for h in history.values():
            for d in h.values():
                if d["dsr_level"] is None:
                    continue
                gap_term = (d["gap_level"] - 50.0) if d["gap_level"] is not None else None
                if gap_term is None:
                    continue
                vals.append(min(100.0, max(0.0, d["dsr_level"] + s * gap_term)))
        if vals:
            zero = sum(1 for v in vals if v <= 0.0) / len(vals)
            w(f"| {s} | {min(vals):.1f} | {statistics.mean(vals):.1f} "
              f"| {max(vals):.1f} | {zero:.1%} |")
    w("")
    w("Note: s=0 ignores the gap (DSR-only); s=1 is the DEC-040 formula. "
      "Missing components defer at every strength — the missing-never-neutral "
      "rule is structural, not parameterized.")
    w("")

    # --- Part 5: assumption boundary -----------------------------------
    w("## 5. What is inherited vs. what is an Atlas assumption")
    w("")
    w("Inherited from already-approved methods (no new science):")
    w("- DSR own-history level: DEC-019 / normalization (min n=20, mid-rank, freshness gates).")
    w("- Credit-gap one-sided vulnerability: DEC-021 (neutral 50 ≤ +2pp, linear to 0 at +10pp).")
    w("- Component roles (CORE_CONDITION / VULNERABILITY_PENALTY / SUPPORTING_CONTEXT): DEC-029.")
    w("- Missing != zero; coverage independent of strength; non-persistence.")
    w("")
    w("New Atlas model assumption introduced by DEC-040:")
    w("- The composition operator itself: additive penalty on the 0–100 scale")
    w("  (penalty = gap_level − 50, i.e. the one-sided curve mapped to a")
    w("  0…−50 subtraction), with hard clamp at 0/100 and the")
    w("  all-components-required completeness rule. The SHAPE (additive,")
    w("  one-sided, unit strength s=1) is the assumption; alternatives s<1")
    w("  or s>1 are evaluated in §4 and remain research-only.")
    w("")

    # --- Part 6: stats table per country --------------------------------
    w("## 6. Per-country scored history summary")
    w("")
    w("| Country | first scored | last scored | n scored | min | mean | max | mean penalty |")
    w("|---|---|---|---|---|---|---|---|")
    for iso3 in COUNTRIES:
        scored = [(p, d) for p, d in history[iso3].items() if d["force_level"] is not None]
        if not scored:
            w(f"| {iso3} | — | — | 0 | — | — | — | — |")
            continue
        vals = [d["force_level"] for _, d in scored]
        pens = [d["penalty"] for _, d in scored if d["penalty"] is not None]
        w(
            f"| {iso3} | {scored[0][0]} | {scored[-1][0]} | {len(scored)} "
            f"| {min(vals):.1f} | {statistics.mean(vals):.1f} | {max(vals):.1f} "
            f"| {statistics.mean(pens):.1f} |"
        )
    w("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out_path}")
    # console summary
    for iso3 in COUNTRIES:
        d = latest_rows[iso3]
        f = lambda v: "—" if v is None else f"{v:.1f}"
        print(
            f"{iso3} {d.get('period')}: DSR {f(d.get('dsr_raw'))}% "
            f"(level {f(d.get('dsr_level'))}) + gap {f(d.get('gap_raw'))}pp "
            f"(level {f(d.get('gap_level'))}, pen {f(d.get('penalty'))}) "
            f"= {f(d.get('force_level'))}"
        )


if __name__ == "__main__":
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    loop.run_until_complete(main())
