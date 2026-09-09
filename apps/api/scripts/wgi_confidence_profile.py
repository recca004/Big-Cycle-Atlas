"""READ-ONLY WGI confidence calibration profile (Sprint 5.16, Parts 1-13).

Research tool that joins WGI latest-vintage score Observations to latest-vintage
indicator diagnostics (LB / UB / SR) using EXACT period + country + base
indicator + expected provider-series identity - never latest-overall, never
adjacent-year borrowing. Analyzes exactly the WGI x3 (RULE_OF_LAW /
CONTROL_OF_CORRUPTION / POLITICAL_STABILITY_WGI_SCORE).

This script is RESEARCH SUPPORT ONLY. It must NOT:
- produce a confidence score or any other score,
- propose or imply a numeric confidence mapping,
- write to the DB (SELECT only),
- become an API endpoint,
- be treated as proof that an empirical distribution is economic truth.

Descriptive statistics describe the current sample; they do not justify a
curve. All values are computed in-memory from read-only queries and printed
to stdout - nothing is persisted.

Example (from apps/api):

    uv run --no-sync python scripts/wgi_confidence_profile.py
"""
import asyncio
import math
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, ".")

from sqlalchemy import func, select

from app.data_sources.wgi_diagnostic_specs import (
    WGI_BASE_INDICATORS,
    WGI_DIAGNOSTIC_SPECS,
    get_wgi_diagnostic_specs,
)
from app.db.session import get_sessionmaker
from app.models import (
    Country,
    DataSource,
    Indicator,
    IndicatorDiagnostic,
    IndicatorDiagnosticKind,
    Observation,
)
from app.models.source_series import SourceSeries

# --- WGI score series external codes (WDI source 2) ---------------------------

_WGI_SCORE_SERIES = {
    "RULE_OF_LAW_WGI_SCORE": "GOV_WGI_RL_SC",
    "CONTROL_OF_CORRUPTION_WGI_SCORE": "GOV_WGI_CC_SC",
    "POLITICAL_STABILITY_WGI_SCORE": "GOV_WGI_PV_SC",
}

_DIMENSION_SHORT = {
    "RULE_OF_LAW_WGI_SCORE": "RL",
    "CONTROL_OF_CORRUPTION_WGI_SCORE": "CC",
    "POLITICAL_STABILITY_WGI_SCORE": "PV",
}

_FP_TOL = 1e-9  # floating-point tolerance for boundary comparison


# --- Data row -----------------------------------------------------------------


@dataclass(frozen=True)
class Row:
    country: str
    base_indicator: str
    year: int
    score: float
    lb: float
    ub: float
    sr: float


# --- Percentile helper --------------------------------------------------------


def _pct(sorted_vals: list[float], pct: float) -> float:
    if len(sorted_vals) == 0:
        return float("nan")
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    cuts = statistics.quantiles(sorted_vals, n=100, method="inclusive")
    return cuts[round(pct) - 1]


def _fmt(v: float | None) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float) and math.isnan(v):
        return "n/a"
    return f"{v:.4g}"


def _describe(vals: list[float]) -> str:
    if not vals:
        return "    (empty)"
    s = sorted(vals)
    return (
        f"    n={len(s)}  min={_fmt(s[0])}  p10={_fmt(_pct(s, 10))}  "
        f"p25={_fmt(_pct(s, 25))}  median={_fmt(statistics.median(s))}  "
        f"p75={_fmt(_pct(s, 75))}  p90={_fmt(_pct(s, 90))}  max={_fmt(s[-1])}"
    )


def _correlation(x: list[float], y: list[float]) -> tuple[float | None, float | None]:
    """Return (pearson, spearman) or (None, None) if undefined."""
    if len(x) < 3 or len(x) != len(y):
        return None, None
    pearson = None
    try:
        pearson = statistics.correlation(x, y)
    except statistics.StatisticsError:
        pass
    # Spearman = Pearson on ranks (average ranks for ties)
    spearman = None
    try:
        rx = _average_ranks(x)
        ry = _average_ranks(y)
        spearman = statistics.correlation(rx, ry)
    except statistics.StatisticsError:
        pass
    return pearson, spearman


def _average_ranks(vals: list[float]) -> list[float]:
    """Average-rank assignment (ties share the mean rank)."""
    indexed = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(indexed):
        j = i
        while j + 1 < len(indexed) and vals[indexed[j + 1]] == vals[indexed[i]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # 1-based
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg_rank
        i = j + 1
    return ranks


# --- Data loading -------------------------------------------------------------


async def _load_rows() -> list[Row]:
    """Join latest-vintage WGI score observations to latest-vintage
    indicator_diagnostics (LB/UB/SR) on exact (country, base indicator,
    source period). Returns one Row per (country, dimension, year) where
    all four values (score, LB, UB, SR) are present."""
    session = get_sessionmaker()()
    try:
        rows: list[Row] = []

        countries = {
            c.iso3: c.id
            for c in (await session.execute(select(Country))).scalars().all()
        }
        # Reverse lookup: country_id -> iso3
        country_by_id = {c_id: c_iso for c_iso, c_id in countries.items()}
        indicators = {
            ind.code: ind.id
            for ind in (await session.execute(select(Indicator))).scalars().all()
        }

        for base_code in WGI_BASE_INDICATORS:
            ind_id = indicators.get(base_code)
            if ind_id is None:
                continue
            score_series_code = _WGI_SCORE_SERIES[base_code]
            score_ss = (
                await session.execute(
                    select(SourceSeries).where(
                        SourceSeries.indicator_id == ind_id,
                        SourceSeries.external_code == score_series_code,
                    )
                )
            ).scalar_one_or_none()
            if score_ss is None:
                continue

            # Latest-vintage score observations for this indicator.
            # Key by (country_id, period_start.date()) - multiple countries
            # share the same period, so date alone would collide.
            score_rows = (
                await session.execute(
                    select(Observation)
                    .where(
                        Observation.indicator_id == ind_id,
                        Observation.source_series_id == score_ss.id,
                    )
                    .order_by(
                        Observation.country_id,
                        Observation.period_start,
                        Observation.vintage_number,
                    )
                )
            ).scalars().all()

            latest_score: dict[tuple[int, date], Observation] = {}
            for obs in score_rows:
                pd = obs.period_start.date() if obs.period_start else None
                if pd is not None:
                    latest_score[(obs.country_id, pd)] = obs  # last wins

            # Latest-vintage diagnostics for this base indicator (all 3 kinds)
            specs = get_wgi_diagnostic_specs(base_code)
            kind_values: dict[tuple[int, date], dict[IndicatorDiagnosticKind, float]] = defaultdict(dict)
            for spec in specs:
                diag_rows = (
                    await session.execute(
                        select(IndicatorDiagnostic)
                        .where(
                            IndicatorDiagnostic.indicator_id == ind_id,
                            IndicatorDiagnostic.diagnostic_kind
                            == spec.diagnostic_kind,
                            IndicatorDiagnostic.provider_source_code
                            == spec.provider_source_code,
                            IndicatorDiagnostic.provider_series_code
                            == spec.provider_series_code,
                        )
                        .order_by(
                            IndicatorDiagnostic.country_id,
                            IndicatorDiagnostic.period_start,
                            IndicatorDiagnostic.vintage_number,
                        )
                    )
                ).scalars().all()
                latest: dict[tuple[int, date], IndicatorDiagnostic] = {}
                for d in diag_rows:
                    pd = d.period_start.date() if d.period_start else None
                    if pd is not None:
                        latest[(d.country_id, pd)] = d
                for key, d in latest.items():
                    kind_values[key][spec.diagnostic_kind] = d.value

            for (cid, pd), score_obs in latest_score.items():
                kv = kind_values.get((cid, pd))
                if kv is None:
                    continue
                lb = kv.get(IndicatorDiagnosticKind.ci_lower_bound)
                ub = kv.get(IndicatorDiagnosticKind.ci_upper_bound)
                sr = kv.get(IndicatorDiagnosticKind.source_count)
                if lb is None or ub is None or sr is None:
                    continue
                iso3 = country_by_id.get(cid)
                if iso3 is None:
                    continue
                rows.append(
                    Row(
                        country=iso3,
                        base_indicator=base_code,
                        year=pd.year,
                        score=score_obs.value,
                        lb=lb,
                        ub=ub,
                        sr=sr,
                    )
                )

        return rows
    finally:
        await session.close()


# --- Analysis sections --------------------------------------------------------


def _section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def _part2_dataset_check(rows: list[Row]) -> None:
    _section("PART 2 - BASE DATASET CHECK")
    print(f"\nTotal rows: {len(rows)}")
    if not rows:
        print("STOP: empty dataset.")
        return

    by_dim = defaultdict(list)
    by_country = defaultdict(list)
    by_year = defaultdict(list)
    for r in rows:
        by_dim[r.base_indicator].append(r)
        by_country[r.country].append(r)
        by_year[r.year].append(r)

    print(f"\nRows by WGI dimension:")
    for dim in WGI_BASE_INDICATORS:
        print(f"  {_DIMENSION_SHORT[dim]} ({dim}): {len(by_dim.get(dim, []))}")

    print(f"\nRows by country:")
    for c in sorted(by_country):
        print(f"  {c}: {len(by_country[c])}")

    print(f"\nRows by year:")
    for y in sorted(by_year):
        print(f"  {y}: {len(by_year[y])}")

    # Completeness checks
    missing_lb = [r for r in rows if r.lb is None]
    missing_ub = [r for r in rows if r.ub is None]
    missing_sr = [r for r in rows if r.sr is None]
    print(f"\nMissing LB: {len(missing_lb)}")
    print(f"Missing UB: {len(missing_ub)}")
    print(f"Missing SR: {len(missing_sr)}")

    # Duplicate identities
    identities = [(r.country, r.base_indicator, r.year) for r in rows]
    dups = [k for k in identities if identities.count(k) > 1]
    print(f"Duplicate identities: {len(set(dups))}")

    # LB > score violations
    lb_violations = [r for r in rows if r.lb > r.score + _FP_TOL]
    ub_violations = [r for r in rows if r.score > r.ub + _FP_TOL]
    print(f"LB > score violations: {len(lb_violations)}")
    print(f"score > UB violations: {len(ub_violations)}")

    if len(rows) != 624:
        print(f"\nWARNING: expected 624 rows, got {len(rows)}")


def _part3_ci_width(rows: list[Row]) -> dict[str, list[float]]:
    _section("PART 3 - CI WIDTH PROFILE")
    enriched = []
    for r in rows:
        ci_width = r.ub - r.lb
        lower_margin = r.score - r.lb
        upper_margin = r.ub - r.score
        enriched.append((r, ci_width, lower_margin, upper_margin))

    pooled_w = [e[1] for e in enriched]
    pooled_lm = [e[2] for e in enriched]
    pooled_um = [e[3] for e in enriched]

    print(f"\nPooled WGI x3:")
    print(f"  ci_width:  {_describe(pooled_w)}")
    print(f"  lower_margin: {_describe(pooled_lm)}")
    print(f"  upper_margin: {_describe(pooled_um)}")

    by_dim = defaultdict(list)
    for r, cw, lm, um in enriched:
        by_dim[r.base_indicator].append((r, cw, lm, um))

    for dim in WGI_BASE_INDICATORS:
        entries = by_dim.get(dim, [])
        if not entries:
            continue
        print(f"\n{_DIMENSION_SHORT[dim]} ({dim}):")
        print(f"  ci_width:  {_describe([e[1] for e in entries])}")
        print(f"  lower_margin: {_describe([e[2] for e in entries])}")
        print(f"  upper_margin: {_describe([e[3] for e in entries])}")

    by_country = defaultdict(list)
    for r, cw, lm, um in enriched:
        by_country[r.country].append((r, cw, lm, um))

    print(f"\nBy country:")
    for c in sorted(by_country):
        entries = by_country[c]
        print(f"  {c}: ci_width {_describe([e[1] for e in entries])}")

    # Latest available year separately
    max_year = max(r.year for r in rows)
    latest = [e for e in enriched if e[0].year == max_year]
    print(f"\nLatest available year ({max_year}):")
    print(f"  ci_width:  {_describe([e[1] for e in latest])}")
    print(f"  lower_margin: {_describe([e[2] for e in latest])}")
    print(f"  upper_margin: {_describe([e[3] for e in latest])}")

    return {"pooled": pooled_w}


def _part4_clipping(rows: list[Row]) -> dict:
    _section("PART 4 - BOUNDARY CLIPPING AUDIT")
    lower_clipped = [r for r in rows if r.lb <= 0 + _FP_TOL]
    upper_clipped = [r for r in rows if r.ub >= 100 - _FP_TOL]
    unclipped = [r for r in rows if r not in lower_clipped and r not in upper_clipped]

    n = len(rows)
    print(f"\nTotal rows: {n}")
    print(f"Lower-bound clipping (LB <= 0): {len(lower_clipped)} ({100*len(lower_clipped)/n:.1f}%)")
    print(f"Upper-bound clipping (UB >= 100): {len(upper_clipped)} ({100*len(upper_clipped)/n:.1f}%)")
    print(f"Unclipped: {len(unclipped)} ({100*len(unclipped)/n:.1f}%)")

    # Clipping by dimension
    print(f"\nClipping by dimension:")
    for dim in WGI_BASE_INDICATORS:
        dim_rows = [r for r in rows if r.base_indicator == dim]
        lc = [r for r in dim_rows if r.lb <= 0 + _FP_TOL]
        uc = [r for r in dim_rows if r.ub >= 100 - _FP_TOL]
        print(f"  {_DIMENSION_SHORT[dim]}: n={len(dim_rows)}  lower_clip={len(lc)}  upper_clip={len(uc)}")

    # Clipping by country
    print(f"\nClipping by country:")
    for c in sorted(set(r.country for r in rows)):
        c_rows = [r for r in rows if r.country == c]
        lc = [r for r in c_rows if r.lb <= 0 + _FP_TOL]
        uc = [r for r in c_rows if r.ub >= 100 - _FP_TOL]
        print(f"  {c}: n={len(c_rows)}  lower_clip={len(lc)}  upper_clip={len(uc)}")

    # Clipping by year
    print(f"\nClipping by year (showing years with any clipping):")
    for y in sorted(set(r.year for r in rows)):
        y_rows = [r for r in rows if r.year == y]
        lc = [r for r in y_rows if r.lb <= 0 + _FP_TOL]
        uc = [r for r in y_rows if r.ub >= 100 - _FP_TOL]
        if lc or uc:
            print(f"  {y}: n={len(y_rows)}  lower_clip={len(lc)}  upper_clip={len(uc)}")

    # CI-width distributions: unclipped vs clipped
    print(f"\nCI-width distributions:")
    print(f"  Unclipped:  {_describe([r.ub - r.lb for r in unclipped])}")
    print(f"  Lower-clipped: {_describe([r.ub - r.lb for r in lower_clipped])}")
    print(f"  Upper-clipped: {_describe([r.ub - r.lb for r in upper_clipped])}")

    # Asymmetry: abs(lower_margin - upper_margin)
    print(f"\nMargin asymmetry |lower_margin - upper_margin|:")
    all_asym = [abs((r.score - r.lb) - (r.ub - r.score)) for r in rows]
    print(f"  All:  {_describe(all_asym)}")
    unclipped_asym = [abs((r.score - r.lb) - (r.ub - r.score)) for r in unclipped]
    lower_asym = [abs((r.score - r.lb) - (r.ub - r.score)) for r in lower_clipped]
    upper_asym = [abs((r.score - r.lb) - (r.ub - r.score)) for r in upper_clipped]
    print(f"  Unclipped: {_describe(unclipped_asym)}")
    print(f"  Lower-clipped: {_describe(lower_asym)}")
    print(f"  Upper-clipped: {_describe(upper_asym)}")

    print(f"\nQuestion: Is raw CI width sufficiently stable to use directly?")
    print(f"  -> See analysis in NORMALIZATION.md decision matrix.")

    return {"lower_clipped": lower_clipped, "upper_clipped": upper_clipped, "unclipped": unclipped}


def _part5_score_vs_width(rows: list[Row], clip_info: dict) -> None:
    _section("PART 5 - CI WIDTH VS SCORE LEVEL")
    scores = [r.score for r in rows]
    widths = [r.ub - r.lb for r in rows]
    p, s = _correlation(scores, widths)
    print(f"\nPooled:")
    print(f"  Pearson (score, ci_width):  {_fmt(p)}")
    print(f"  Spearman (score, ci_width): {_fmt(s)}")

    for dim in WGI_BASE_INDICATORS:
        dim_rows = [r for r in rows if r.base_indicator == dim]
        ds = [r.score for r in dim_rows]
        dw = [r.ub - r.lb for r in dim_rows]
        p, s = _correlation(ds, dw)
        print(f"\n{_DIMENSION_SHORT[dim]}:")
        print(f"  Pearson:  {_fmt(p)}")
        print(f"  Spearman: {_fmt(s)}")

    unclipped = clip_info["unclipped"]
    lower_c = clip_info["lower_clipped"]
    upper_c = clip_info["upper_clipped"]

    print(f"\nUnclipped rows:")
    us = [r.score for r in unclipped]
    uw = [r.ub - r.lb for r in unclipped]
    p, s = _correlation(us, uw)
    print(f"  Pearson:  {_fmt(p)}")
    print(f"  Spearman: {_fmt(s)}")

    print(f"\nLower-clipped rows:")
    ls = [r.score for r in lower_c]
    lw = [r.ub - r.lb for r in lower_c]
    p, s = _correlation(ls, lw)
    print(f"  Pearson:  {_fmt(p)}")
    print(f"  Spearman: {_fmt(s)}")

    print(f"\nUpper-clipped rows:")
    us = [r.score for r in upper_c]
    uw = [r.ub - r.lb for r in upper_c]
    p, s = _correlation(us, uw)
    print(f"  Pearson:  {_fmt(p)}")
    print(f"  Spearman: {_fmt(s)}")

    print(f"\nQuestion: Does high/low governance level distort observed width?")
    print(f"  -> See analysis in NORMALIZATION.md decision matrix.")


def _part6_source_count(rows: list[Row]) -> None:
    _section("PART 6 - SOURCE COUNT (SR) PROFILE")
    srs = [r.sr for r in rows]
    print(f"\nPooled:")
    print(f"  {_describe(srs)}")

    for dim in WGI_BASE_INDICATORS:
        dim_srs = [r.sr for r in rows if r.base_indicator == dim]
        print(f"\n{_DIMENSION_SHORT[dim]}:")
        print(f"  {_describe(dim_srs)}")

    print(f"\nBy country:")
    for c in sorted(set(r.country for r in rows)):
        c_srs = [r.sr for r in rows if r.country == c]
        print(f"  {c}: {_describe(c_srs)}")

    print(f"\nBy year (median SR):")
    by_year = defaultdict(list)
    for r in rows:
        by_year[r.year].append(r.sr)
    for y in sorted(by_year):
        print(f"  {y}: median={_fmt(statistics.median(by_year[y]))}  n={len(by_year[y])}")

    # Temporal trend: SR vs year
    years = [r.year for r in rows]
    p, s = _correlation(years, srs)
    print(f"\nTemporal trend (SR vs year):")
    print(f"  Pearson:  {_fmt(p)}")
    print(f"  Spearman: {_fmt(s)}")

    print(f"\nQuestion: Would SR-based confidence partly encode 'newer = more sources'?")
    print(f"  -> See analysis in NORMALIZATION.md decision matrix.")


def _part7_width_vs_sr(rows: list[Row], clip_info: dict) -> None:
    _section("PART 7 - CI WIDTH VS SR OVERLAP")
    srs = [r.sr for r in rows]
    widths = [r.ub - r.lb for r in rows]
    p, s = _correlation(srs, widths)
    print(f"\nPooled:")
    print(f"  Pearson (SR, ci_width):  {_fmt(p)}")
    print(f"  Spearman (SR, ci_width): {_fmt(s)}")

    for dim in WGI_BASE_INDICATORS:
        dim_rows = [r for r in rows if r.base_indicator == dim]
        ds = [r.sr for r in dim_rows]
        dw = [r.ub - r.lb for r in dim_rows]
        p, s = _correlation(ds, dw)
        print(f"\n{_DIMENSION_SHORT[dim]}:")
        print(f"  Pearson:  {_fmt(p)}")
        print(f"  Spearman: {_fmt(s)}")

    unclipped = clip_info["unclipped"]
    us = [r.sr for r in unclipped]
    uw = [r.ub - r.lb for r in unclipped]
    p, s = _correlation(us, uw)
    print(f"\nUnclipped rows:")
    print(f"  Pearson:  {_fmt(p)}")
    print(f"  Spearman: {_fmt(s)}")

    lower_c = clip_info["lower_clipped"]
    if len(lower_c) >= 3:
        ls = [r.sr for r in lower_c]
        lw = [r.ub - r.lb for r in lower_c]
        p, s = _correlation(ls, lw)
        print(f"\nLower-clipped rows (n={len(lower_c)}):")
        print(f"  Pearson:  {_fmt(p)}")
        print(f"  Spearman: {_fmt(s)}")
    else:
        print(f"\nLower-clipped rows: n={len(lower_c)} (insufficient for correlation)")

    upper_c = clip_info["upper_clipped"]
    if len(upper_c) >= 3:
        us = [r.sr for r in upper_c]
        uw = [r.ub - r.lb for r in upper_c]
        p, s = _correlation(us, uw)
        print(f"\nUpper-clipped rows (n={len(upper_c)}):")
        print(f"  Pearson:  {_fmt(p)}")
        print(f"  Spearman: {_fmt(s)}")
    else:
        print(f"\nUpper-clipped rows: n={len(upper_c)} (insufficient for correlation)")

    # Median CI width by integer SR
    print(f"\nMedian CI width by integer SR value:")
    by_sr = defaultdict(list)
    for r in rows:
        by_sr[int(r.sr)].append(r.ub - r.lb)
    for sr_val in sorted(by_sr):
        vals = by_sr[sr_val]
        print(f"  SR={sr_val}: n={len(vals)}  median={_fmt(statistics.median(vals))}")

    print(f"\nQuestion: Does SR add clearly distinct information after CI width?")
    print(f"  -> See analysis in NORMALIZATION.md decision matrix.")


def _part8_dimensions(rows: list[Row], clip_info: dict) -> None:
    _section("PART 8 - DIMENSION DIFFERENCES")
    for dim in WGI_BASE_INDICATORS:
        dim_rows = [r for r in rows if r.base_indicator == dim]
        widths = [r.ub - r.lb for r in dim_rows]
        srs = [r.sr for r in dim_rows]
        lc = [r for r in dim_rows if r.lb <= 0 + _FP_TOL]
        uc = [r for r in dim_rows if r.ub >= 100 - _FP_TOL]
        print(f"\n{_DIMENSION_SHORT[dim]} ({dim}):")
        print(f"  CI width: {_describe(widths)}")
        print(f"  SR:      {_describe(srs)}")
        print(f"  lower_clip={len(lc)}  upper_clip={len(uc)}  clip_rate={100*(len(lc)+len(uc))/len(dim_rows):.1f}%")

    print(f"\nQuestion: Would one global calibration systematically favor/penalize")
    print(f"  one governance dimension?")
    print(f"  -> See analysis in NORMALIZATION.md decision matrix.")


def _part9_countries(rows: list[Row], clip_info: dict) -> None:
    _section("PART 9 - COUNTRY DIFFERENCES")
    for c in sorted(set(r.country for r in rows)):
        c_rows = [r for r in rows if r.country == c]
        widths = [r.ub - r.lb for r in c_rows]
        srs = [r.sr for r in c_rows]
        lc = [r for r in c_rows if r.lb <= 0 + _FP_TOL]
        uc = [r for r in c_rows if r.ub >= 100 - _FP_TOL]
        clip_rate = 100 * (len(lc) + len(uc)) / len(c_rows) if c_rows else 0
        s_sorted = sorted(widths)
        print(f"\n{c}:")
        print(f"  CI width: {_describe(widths)}")
        print(f"  SR:      {_describe(srs)}")
        print(f"  clip_rate={clip_rate:.1f}%  (lower={len(lc)} upper={len(uc)})")

    print(f"\nQuestion: Would a pooled calibration mechanically rank countries by")
    print(f"  measurement-system richness rather than represent uncertainty?")
    print(f"  -> See analysis in NORMALIZATION.md decision matrix.")


def _part10_calibration_leakage() -> None:
    _section("PART 10 - TIME / CALIBRATION LEAKAGE")
    options = [
        ("A. Fixed provider-scale mapping",
         "A fixed function from raw CI width (or SR) to a confidence component, calibrated once.",
         "Simple, transparent, no historical data needed.",
         "No empirical grounding for the mapping shape; arbitrary.",
         "Same for all snapshots - no leakage.",
         "No future-data leakage.",
         "Absolute confidence (not relative to a distribution).",
         "Arbitrary semantics unless externally justified."),
        ("B. Expanding own-history precision percentile",
         "Country's own expanding history of CI widths -> percentile of current width.",
         "Self-contained per country; adapts to each country's measurement history.",
         "Early years have tiny n; percentile unstable; may encode improvement over time as confidence change.",
         "As-of safe (expanding only, no future data).",
         "No future-data leakage (if strictly expanding).",
         "Relative confidence (relative to own history).",
         "Confidence would drift as measurement systems improve - may not reflect current quality."),
        ("C. Expanding same-dimension global/cross-country calibration",
         "All countries' expanding CI-width history for one dimension -> percentile.",
         "More data than own-history; cross-country context.",
         "Pooled across countries with different measurement systems; may encode development status.",
         "As-of safe (expanding only).",
         "No future-data leakage (if strictly expanding).",
         "Relative confidence (relative to cross-country distribution).",
         "Country identity becomes a hidden prior via the pooled distribution."),
        ("D. Full-history empirical percentile",
         "Percentile using ALL history (including future relative to a historical snapshot).",
         "Maximum data; stable estimates.",
         "FUTURE DATA LEAKAGE - using later distribution info for earlier snapshots.",
         "NOT as-of safe.",
         "LEAKS future data - cannot be called backtest-safe.",
         "Relative confidence.",
         "Cannot be used for historical/backtest scoring."),
        ("E. tracked_8 cross-sectional percentile",
         "Current CI width ranked within tracked_8 at the same snapshot.",
         "Consistent with the relative-score universe.",
         "n=8 is a weak distribution; tracked_8 must never masquerade as global measurement quality.",
         "As-of safe (same snapshot).",
         "No future-data leakage.",
         "Relative confidence (within tracked_8).",
         "Encodes relative position, not absolute measurement quality."),
        ("F. Diagnostics-only / no scalar yet",
         "Keep LB/UB/SR as diagnostic provenance; do not collapse to a scalar.",
         "No arbitrary mapping; preserves all information for future use.",
         "No numeric confidence component from measurement uncertainty.",
         "N/A (no scalar produced).",
         "No leakage risk.",
         "No scalar (None).",
         "Confidence composition stays open until a defensible mapping is approved."),
    ]
    for title, meaning, benefits, problems, asof, leakage, abs_rel, arbitrary in options:
        print(f"\n{title}")
        print(f"  Meaning: {meaning}")
        print(f"  Benefits: {benefits}")
        print(f"  Problems: {problems}")
        print(f"  As-of behavior: {asof}")
        print(f"  Future leakage: {leakage}")
        print(f"  Absolute vs relative: {abs_rel}")
        print(f"  Arbitrary semantics: {arbitrary}")

    print(f"\nRules:")
    print(f"  - FULL-HISTORY calibration (D) may be used descriptively here but must")
    print(f"    NOT later be called historical/as-of-safe.")
    print(f"  - tracked_8 (E) must never masquerade as global measurement quality.")


def _part11_freshness_composition() -> None:
    _section("PART 11 - FRESHNESS COMPOSITION")
    options = [
        ("Multiplication",
         "confidence = freshness_factor * measurement_uncertainty_factor",
         "A single bad component tanks the whole - semantically correct for 'AND' trust."),
        ("Weighted arithmetic mean",
         "confidence = w1*freshness + w2*measurement_uncertainty",
         "A bad component only partially reduces confidence - may overstate trust."),
        ("Weighted geometric mean",
         "confidence = freshness^w1 * measurement_uncertainty^w2",
         "Balances - a zero in one component zeroes the product; less harsh than pure multiplication on partial degradation."),
        ("Minimum / bottleneck",
         "confidence = min(freshness_factor, measurement_uncertainty_factor)",
         "The weakest link dominates - conservative; may be too harsh."),
        ("Separate diagnostics without scalar composition",
         "Keep freshness_factor and measurement_uncertainty as separate provenance; no scalar confidence yet.",
         "No arbitrary composition; preserves all information; defers the aggregation decision."),
    ]
    for title, formula, note in options:
        print(f"\n{title}")
        print(f"  Formula: {formula}")
        print(f"  Note: {note}")

    print(f"\nSemantic examples:")
    examples = [
        ("A: freshness 1.0, high measurement uncertainty",
         "The score is fresh but poorly measured - confidence should be LOW (not 1.0)."),
        ("B: freshness 0.6, low measurement uncertainty",
         "The score is somewhat stale but well measured - confidence should be moderate, not 0.6."),
        ("C: freshness 1.0, measurement uncertainty missing",
         "Fresh score, unknown measurement quality - confidence is NOT 1 (missing != perfect);"),
        ("D: freshness 0.2 but still technically usable",
         "Very stale but still usable - confidence is low but NOT zero; the score is still produced."),
    ]
    for title, note in examples:
        print(f"  {title}")
        print(f"    -> {note}")

    print(f"\nThe final methodology must preserve:")
    print(f"  - confidence != freshness")
    print(f"  - missing uncertainty != confidence 1")
    print(f"  - missing uncertainty != confidence 0")
    print(f"\nNo number is required this sprint.")


def _part12_source_quality() -> None:
    _section("PART 12 - SOURCE QUALITY")
    print(f"\nWGI is a perception-based composite published by the World Bank/WGI project.")
    print(f"It is NOT an official_primary source (like a central bank balance sheet).")
    print(f"It is a perception_composite - aggregated expert assessments + survey data.")
    print(f"\nAssessment:")
    print(f"  - source_quality should remain PROVENANCE ONLY for now.")
    print(f"  - It may later become an ordinal enum (official_primary / official_republished /")
    print(f"    proxy_measure / perception_composite).")
    print(f"  - It should NOT act as a hard cap on confidence (no evidence for a specific cap value).")
    print(f"  - It should remain OUTSIDE numeric confidence entirely until a calibrated,")
    print(f"    versioned mapping is approved.")
    print(f"\nNo numeric constant. No 'World Bank = 0.95' or 'WGI = 0.85'.")


def _part13_method_sufficiency() -> None:
    _section("PART 13 - METHOD SUFFICIENCY")
    print(f"\nFor WGI DIRECT_0_100:")
    print(f"  - Level: no own-history minimum-sample issue (the score IS the raw value).")
    print(f"  - Relative: requires complete tracked_8 universe (8/8 or nobody).")
    print(f"  - Momentum: may be missing because historical anchors are unavailable (biennial gaps,")
    print(f"    anchor tolerance).")
    print(f"\nKey question: should confidence be ONE scalar for the entire NormalizedSignal,")
    print(f"  or eventually dimension-specific?")
    print(f"\nExample: WGI current level may be well measured, while 5y momentum is unavailable.")
    print(f"  A single scalar confidence would HIDE that distinction.")
    print(f"\nRecommendation: confidence should eventually be PER-DIMENSION, not one scalar:")
    print(f"  - level_confidence (measurement uncertainty + freshness of the level observation)")
    print(f"  - relative_confidence (universe completeness + freshness of all members)")
    print(f"  - momentum_confidence (anchor availability + anchor freshness + measurement uncertainty)")
    print(f"\nThis preserves the distinction: 'level is well measured but momentum is unavailable'")
    print(f"  is different from 'level is poorly measured'.")
    print(f"\nDo NOT implement a new schema this sprint - methodology recommendation only.")


# --- Main ---------------------------------------------------------------------


async def main() -> None:
    print("WGI Confidence Calibration Profile (Sprint 5.16)")
    print("=" * 70)
    print("READ-ONLY research tool. No writes. No confidence score produced.")
    print("Descriptive statistics only - not proof of economic truth.")
    print()

    rows = await _load_rows()

    _part2_dataset_check(rows)
    if not rows:
        return

    _part3_ci_width(rows)
    clip_info = _part4_clipping(rows)
    _part5_score_vs_width(rows, clip_info)
    _part6_source_count(rows)
    _part7_width_vs_sr(rows, clip_info)
    _part8_dimensions(rows, clip_info)
    _part9_countries(rows, clip_info)
    _part10_calibration_leakage()
    _part11_freshness_composition()
    _part12_source_quality()
    _part13_method_sufficiency()

    print(f"\n{'=' * 70}")
    print("  END OF PROFILE - see NORMALIZATION.md for the decision matrix + verdict")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())

