"""Strategy definitions (Mission 5 §26).

Deterministic, versioned strategy specs. Benchmark strategies work on
market data alone — no Big Cycle classifier dependency. Regime-based
strategies stay gated behind their own evidence requirements (§31).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

STRATEGY_ENGINE_VERSION = "strategy-engine-v0.1"


class StrategyKind(str, Enum):
    buy_and_hold = "buy_and_hold"
    fixed_weight = "fixed_weight"        # buy at start, weights drift
    periodic_rebalance = "periodic_rebalance"
    equal_weight = "equal_weight"        # periodic rebalance to 1/N
    cash_benchmark = "cash_benchmark"


class EvaluationCategory(str, Enum):
    """§31 — never combined, each assessed separately."""
    arithmetic_demo = "arithmetic_demo"
    retrospective_market = "retrospective_market"
    retrospective_macro_regime = "retrospective_macro_regime"
    strict_eligible = "strict_eligible"


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    version: str
    kind: StrategyKind
    allocations: tuple[tuple[str, float], ...]   # (instrument_code, weight)
    rebalance: str = "annual"                    # none|annual|quarterly|monthly
    category: EvaluationCategory = EvaluationCategory.retrospective_market
    description: str = ""

    def validate(self) -> list[str]:
        errors = []
        if self.kind is not StrategyKind.cash_benchmark:
            if not self.allocations:
                errors.append("allocations required")
            total = sum(w for _, w in self.allocations)
            if self.kind in (
                StrategyKind.fixed_weight,
                StrategyKind.periodic_rebalance,
                StrategyKind.buy_and_hold,
            ) and abs(total - 1.0) > 1e-6:
                errors.append(f"weights must sum to 1.0 (got {total:.4f})")
            if any(w < 0 for _, w in self.allocations):
                errors.append("negative weights not allowed (long-only)")
            if len({c for c, _ in self.allocations}) != len(self.allocations):
                errors.append("duplicate instrument codes")
        if self.rebalance not in ("none", "annual", "quarterly", "monthly"):
            errors.append(f"unknown rebalance {self.rebalance!r}")
        return errors


BENCHMARK_STRATEGIES: dict[str, StrategySpec] = {
    "buy_and_hold_us_equity": StrategySpec(
        "buy_and_hold_us_equity", "v1", StrategyKind.buy_and_hold,
        (("USA_EQUITY_PRICE_INDEX", 1.0),),
        rebalance="none",
        description="100% US equity price index, no rebalancing",
    ),
    "cash_us": StrategySpec(
        "cash_us", "v1", StrategyKind.cash_benchmark, (),
        description="All cash — flat value (no interest modelled)",
    ),
}


def fixed_weight_strategy(
    allocations: dict[str, float], rebalance: str = "annual",
    version: str = "v1",
) -> StrategySpec:
    return StrategySpec(
        strategy_id="custom_fixed_weight",
        version=version,
        kind=StrategyKind.periodic_rebalance,
        allocations=tuple(sorted(allocations.items())),
        rebalance=rebalance,
        description="user-specified fixed weights, periodic rebalance",
    )


def equal_weight_strategy(
    instruments: list[str], rebalance: str = "annual", version: str = "v1"
) -> StrategySpec:
    n = len(instruments)
    return StrategySpec(
        strategy_id="custom_equal_weight",
        version=version,
        kind=StrategyKind.equal_weight,
        allocations=tuple(sorted((c, 1.0 / n) for c in instruments)),
        rebalance=rebalance,
        description="equal 1/N weights, periodic rebalance",
    )
