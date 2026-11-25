"""Experimental market regime engine (Mission 5 §19-§22).

Separate from the Big Cycle classifier: the Big Cycle models long-term
national conditions; this engine classifies shorter-horizon economic and
financial conditions — a simple growth-inflation framework plus separate
financial-conditions measurements.

Cadence is ANNUAL for the growth-inflation core (GDP growth and CPI are
annual in the Atlas) — monthly financial conditions are reported as
measurements, not forced into a finer regime grid the data can't support.

All thresholds are declared model assumptions in RegimeConfig, never
universal market laws.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

REGIME_ENGINE_VERSION = "market-regime-v0.1"


class GrowthDirection(str, Enum):
    improving = "improving"
    weakening = "weakening"
    unknown = "unknown"


class InflationDirection(str, Enum):
    rising = "rising"
    falling = "falling"
    unknown = "unknown"


class Regime(str, Enum):
    reflation = "REFLATION"                    # improving growth + rising inflation
    goldilocks = "GOLDILOCKS"                  # improving growth + falling inflation
    stagflation = "STAGFLATION"                # weakening growth + rising inflation
    disinflation_slowdown = "DISINFLATION_SLOWDOWN"  # weakening + falling
    unclassified = "UNCLASSIFIED"


_REGIME_MAP = {
    (GrowthDirection.improving, InflationDirection.rising): Regime.reflation,
    (GrowthDirection.improving, InflationDirection.falling): Regime.goldilocks,
    (GrowthDirection.weakening, InflationDirection.rising): Regime.stagflation,
    (GrowthDirection.weakening, InflationDirection.falling):
        Regime.disinflation_slowdown,
}


@dataclass(frozen=True)
class RegimeConfig:
    """Declared assumptions — versioned, not validated constants."""
    model_id: str = "market_regime_growth_inflation_v1"
    version: str = "v0.1"
    # Direction thresholds (percentage points). A change smaller than eps
    # is treated as "flat" and carries the PRIOR direction forward.
    growth_eps: float = 0.25
    inflation_eps: float = 0.25
    # Minimum inputs: both current AND previous year needed per signal.
    min_years: int = 2


def direction(
    current: float | None, previous: float | None, eps: float,
    rising_type: type,
) -> GrowthDirection | InflationDirection | None:
    """Classify a series' direction; sub-eps changes return None
    (caller carries prior direction — no direction is never guessed)."""
    if current is None or previous is None:
        return None
    delta = current - previous
    if rising_type is GrowthDirection:
        if delta > eps:
            return GrowthDirection.improving
        if delta < -eps:
            return GrowthDirection.weakening
    else:
        if delta > eps:
            return InflationDirection.rising
        if delta < -eps:
            return InflationDirection.falling
    return None


@dataclass(frozen=True)
class RegimeYear:
    year: int
    regime: Regime
    growth_direction: GrowthDirection
    inflation_direction: InflationDirection
    gdp_growth: float | None
    inflation: float | None
    missing_inputs: tuple[str, ...]
    reason: str


def classify_years(
    gdp_by_year: dict[int, float | None],
    cpi_by_year: dict[int, float | None],
    cfg: RegimeConfig = RegimeConfig(),
) -> list[RegimeYear]:
    """Classify each year with enough inputs.

    A year needs its own value AND a prior-year value to form a
    direction. Sub-eps moves carry the previous direction forward;
    the first year always reports unknowns (never fabricated).
    """
    years = sorted(set(gdp_by_year) | set(cpi_by_year))
    out: list[RegimeYear] = []
    g_dir: GrowthDirection | None = None
    i_dir: InflationDirection | None = None
    for y in years:
        g, g_prev = gdp_by_year.get(y), gdp_by_year.get(y - 1)
        c, c_prev = cpi_by_year.get(y), cpi_by_year.get(y - 1)
        missing = tuple(
            name for name, v in (
                ("gdp_growth", g), ("gdp_growth_prev", g_prev),
                ("inflation_cpi", c), ("inflation_cpi_prev", c_prev),
            ) if v is None
        )
        g_new = direction(g, g_prev, cfg.growth_eps, GrowthDirection)
        i_new = direction(c, c_prev, cfg.inflation_eps, InflationDirection)
        if g_new is not None:
            g_dir = g_new
        if i_new is not None:
            i_dir = i_new
        g_eff = g_dir or GrowthDirection.unknown
        i_eff = i_dir or InflationDirection.unknown
        if GrowthDirection.unknown in (g_eff,) or i_eff is InflationDirection.unknown:
            regime = Regime.unclassified
        else:
            regime = _REGIME_MAP.get((g_eff, i_eff), Regime.unclassified)
        out.append(RegimeYear(
            year=y, regime=regime,
            growth_direction=g_eff, inflation_direction=i_eff,
            gdp_growth=g, inflation=c,
            missing_inputs=missing,
            reason="classified" if regime is not Regime.unclassified
            else f"missing {missing}" if missing else "direction not yet established",
        ))
    return out


@dataclass(frozen=True)
class FinancialConditions:
    """§21 separate measurements — never blended into a universal index."""
    year: int
    policy_rate: float | None
    long_yield: float | None
    real_rate_proxy: float | None      # policy_rate - inflation (stated as proxy)
    currency_return: float | None      # annual change in the country's FX quote
    missing: tuple[str, ...]
