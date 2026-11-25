"""Experimental composite engine — Mission 2 §11 (Models A/B/C/D).

Pure functions over ForceSignal sequences. Every result carries full
provenance: included/excluded forces, weights, compatibility verdicts,
coverage, limitations, methodology state, backtest flag.

Nothing here is APPROVED_PRODUCTION — all composite scores are EXPERIMENTAL
and labelled so; they must never appear in the force-score endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.cycle.force_signal import ForceSignal
from app.research.semantics import (
    FORCE_DOMAINS,
    OVERLAP_GROUPS,
    level_compatibility,
)

COMPOSITE_ENGINE_VERSION = "composite-v0.1"


class MissingPolicy(str):
    # not an Enum to keep the wire contract literal
    STRICT = "strict"                    # any missing scored force -> no result
    RENORMALIZE = "renormalize"          # explicit experimental option
    MIN_COVERAGE = "min_coverage"        # result if covered >= threshold


@dataclass(frozen=True)
class CompositeModelSpec:
    model_id: str
    version: str
    kind: str                        # "equal" | "domain" | "overlap_adjusted" | "fixed_subset"
    eligible_forces: frozenset[str]  # forces the model may consider
    missing_policy: str = MissingPolicy.MIN_COVERAGE
    min_coverage: float = 0.5        # fraction of eligible forces present
    allow_renormalize: bool = False
    notes: str = ""


@dataclass(frozen=True)
class ForceContribution:
    force_code: str
    value: float
    weight: float                  # effective weight after model rules
    semantics_ok: bool


@dataclass(frozen=True)
class CompositeResult:
    model_id: str
    model_version: str
    methodology_status: str        # always "experimental"
    country_iso3: str
    scoring_period: str
    score: float | None            # None = coverage gate failed
    included_forces: tuple[str, ...]
    excluded_forces: tuple[ForceContribution | str, ...]
    missing_forces: tuple[str, ...]
    weights: dict[str, float]
    coverage_ratio: float
    contributions: tuple[ForceContribution, ...]
    warnings: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    backtest_safe: bool = False
    # Which information-selection mode produced the inputs (§23).
    # Retrospective latest-vintage unless a strict/assumption spec ran.
    execution_mode: str = "retrospective_latest_vintage"


def _partition(
    spec: CompositeModelSpec,
    signals: dict[str, ForceSignal],
) -> tuple[list[tuple[str, float]], list[str], list[str]]:
    """Split signals into (scored, missing, excluded) for this model."""
    scored: list[tuple[str, float]] = []
    missing: list[str] = []
    excluded: list[str] = []
    for force_code in sorted(spec.eligible_forces):
        ok, reason = level_compatibility(force_code)
        if not ok:
            excluded.append(f"{force_code}: {reason}")
            continue
        sig = signals.get(force_code)
        if sig is None or sig.level_score is None:
            missing.append(force_code)
        else:
            scored.append((force_code, sig.level_score))
    return scored, missing, excluded


def _coverage_gate(
    spec: CompositeModelSpec, n_scored: int, n_missing: int
) -> bool:
    if spec.missing_policy == MissingPolicy.STRICT:
        return n_missing == 0
    if spec.missing_policy == MissingPolicy.MIN_COVERAGE:
        total = n_scored + n_missing
        return total > 0 and (n_scored / total) >= spec.min_coverage
    return True  # RENORMALIZE — explicit opt-in


def _warn_weights(
    spec: CompositeModelSpec, n_scored: int, n_missing: int
) -> tuple[str, ...]:
    warnings = []
    if spec.missing_policy == MissingPolicy.RENORMALIZE:
        warnings.append(
            "missing weights renormalized — an EXPLICIT experimental option; "
            "comparability across countries with different missing patterns "
            "is weakened"
        )
    if n_missing:
        warnings.append(
            f"{n_missing} eligible force(s) missing — result is NOT a full "
            "composite; missing-weight redistribution is never silent"
        )
    return tuple(warnings)


def model_a_equal(
    spec: CompositeModelSpec,
    signals: dict[str, ForceSignal],
    country_iso3: str,
    scoring_period: str,
) -> CompositeResult:
    """Model A — equal-force benchmark. Reference calculation only; equal
    weighting is NOT scientifically approved."""
    scored, missing, excluded = _partition(spec, signals)
    if not _coverage_gate(spec, len(scored), len(missing)):
        return CompositeResult(
            model_id=spec.model_id, model_version=spec.version,
            methodology_status="experimental",
            country_iso3=country_iso3, scoring_period=scoring_period,
            score=None, included_forces=tuple(f for f, _ in scored),
            excluded_forces=tuple(excluded), missing_forces=tuple(missing),
            weights={}, coverage_ratio=0.0, contributions=(),
            warnings=("coverage gate failed",),
        )
    n = len(scored)
    w = 1.0 / n if n else 0.0
    contribs = tuple(
        ForceContribution(f, v, w, True) for f, v in scored
    )
    score = sum(v * w for _, v, w in
                ((c.force_code, c.value, c.weight) for c in contribs)) if n else None
    return CompositeResult(
        model_id=spec.model_id, model_version=spec.version,
        methodology_status="experimental",
        country_iso3=country_iso3, scoring_period=scoring_period,
        score=score,
        included_forces=tuple(c.force_code for c in contribs),
        excluded_forces=tuple(excluded),
        missing_forces=tuple(missing),
        weights={c.force_code: c.weight for c in contribs},
        coverage_ratio=n / (n + len(missing)) if (n + len(missing)) else 0.0,
        contributions=contribs,
        warnings=_warn_weights(spec, n, len(missing)),
        limitations=(
            "Equal weighting is a benchmark, not a validated model",
            "mixes absolute-bounded and reference-relative semantics — "
            "compatible by rule, not by proof",
        ),
    )


def model_b_domain(
    spec: CompositeModelSpec,
    signals: dict[str, ForceSignal],
    country_iso3: str,
    scoring_period: str,
) -> CompositeResult:
    """Model B — domain-balanced: equal weight per populated DOMAIN, equal
    within domain. Prevents the 4-force governance cluster from receiving
    4/9 of the weight."""
    scored, missing, excluded = _partition(spec, signals)
    if not _coverage_gate(spec, len(scored), len(missing)):
        return CompositeResult(
            model_id=spec.model_id, model_version=spec.version,
            methodology_status="experimental",
            country_iso3=country_iso3, scoring_period=scoring_period,
            score=None, included_forces=tuple(f for f, _ in scored),
            excluded_forces=tuple(excluded), missing_forces=tuple(missing),
            weights={}, coverage_ratio=0.0, contributions=(),
            warnings=("coverage gate failed",),
        )
    by_domain: dict[str, list[tuple[str, float]]] = {}
    for f, v in scored:
        by_domain.setdefault(FORCE_DOMAINS.get(f, "other"), []).append((f, v))
    n_domains = len(by_domain)
    contribs: list[ForceContribution] = []
    score = 0.0
    for domain, members in sorted(by_domain.items()):
        dw = 1.0 / n_domains / len(members)
        for f, v in members:
            contribs.append(ForceContribution(f, v, dw, True))
            score += v * dw
    return CompositeResult(
        model_id=spec.model_id, model_version=spec.version,
        methodology_status="experimental",
        country_iso3=country_iso3, scoring_period=scoring_period,
        score=score,
        included_forces=tuple(c.force_code for c in contribs),
        excluded_forces=tuple(excluded),
        missing_forces=tuple(missing),
        weights={c.force_code: c.weight for c in contribs},
        coverage_ratio=len(scored) / (len(scored) + len(missing)),
        contributions=tuple(contribs),
        warnings=_warn_weights(spec, len(scored), len(missing)),
        limitations=(
            "Domain grouping is a candidate classification, not validated",
            "equal domain weights assumed — no empirical basis claimed",
        ),
    )


def model_c_overlap_adjusted(
    spec: CompositeModelSpec,
    signals: dict[str, ForceSignal],
    country_iso3: str,
    scoring_period: str,
) -> CompositeResult:
    """Model C — overlap-adjusted: forces sharing an OVERLAP_GROUP get their
    combined weight capped at one group share (equal across groups and
    ungrouped forces)."""
    scored, missing, excluded = _partition(spec, signals)
    if not _coverage_gate(spec, len(scored), len(missing)):
        return CompositeResult(
            model_id=spec.model_id, model_version=spec.version,
            methodology_status="experimental",
            country_iso3=country_iso3, scoring_period=scoring_period,
            score=None, included_forces=tuple(f for f, _ in scored),
            excluded_forces=tuple(excluded), missing_forces=tuple(missing),
            weights={}, coverage_ratio=0.0, contributions=(),
            warnings=("coverage gate failed",),
        )
    scored_codes = {f for f, _ in scored}
    # Partition scored forces into units: each overlap group present = 1 unit;
    # each ungrouped force = 1 unit.
    units: list[list[tuple[str, float]]] = []
    used: set[str] = set()
    for group in OVERLAP_GROUPS:
        members = [(f, v) for f, v in scored if f in group]
        if members:
            units.append(members)
            used.update(f for f, _ in members)
    for f, v in scored:
        if f not in used:
            units.append([(f, v)])
    n_units = len(units)
    contribs: list[ForceContribution] = []
    score = 0.0
    for unit in units:
        uw = 1.0 / n_units / len(unit)
        for f, v in unit:
            contribs.append(ForceContribution(f, v, uw, True))
            score += v * uw
    warnings = list(_warn_weights(spec, len(scored), len(missing)))
    grouped = sorted(used)
    if grouped:
        warnings.append(
            f"overlap-adjusted: {', '.join(grouped)} share group weights"
        )
    return CompositeResult(
        model_id=spec.model_id, model_version=spec.version,
        methodology_status="experimental",
        country_iso3=country_iso3, scoring_period=scoring_period,
        score=score,
        included_forces=tuple(c.force_code for c in contribs),
        excluded_forces=tuple(excluded),
        missing_forces=tuple(missing),
        weights={c.force_code: c.weight for c in contribs},
        coverage_ratio=len(scored) / (len(scored) + len(missing)),
        contributions=tuple(contribs),
        warnings=tuple(warnings),
        limitations=(
            "Conceptual overlap groups are hand-declared — no correlation "
            "estimation claimed (sample too small)",
        ),
    )


def model_d_fixed_subset(
    spec: CompositeModelSpec,
    signals: dict[str, ForceSignal],
    country_iso3: str,
    scoring_period: str,
) -> CompositeResult:
    """Model D — fixed comparable subset: only spec.eligible_forces; STRICT
    missing policy by construction. Countries missing any member are not
    comparable — result is None with the reason recorded."""
    scored, missing, excluded = _partition(spec, signals)
    strict = CompositeModelSpec(
        model_id=spec.model_id, version=spec.version, kind=spec.kind,
        eligible_forces=spec.eligible_forces,
        missing_policy=MissingPolicy.STRICT,
    )
    if not _coverage_gate(strict, len(scored), len(missing)):
        return CompositeResult(
            model_id=spec.model_id, model_version=spec.version,
            methodology_status="experimental",
            country_iso3=country_iso3, scoring_period=scoring_period,
            score=None, included_forces=tuple(f for f, _ in scored),
            excluded_forces=tuple(excluded), missing_forces=tuple(missing),
            weights={}, coverage_ratio=0.0, contributions=(),
            warnings=(
                "fixed-subset model: not all members present — country is "
                "not comparable under this model (never silently rescored)",
            ),
        )
    n = len(scored)
    w = 1.0 / n if n else 0.0
    contribs = tuple(ForceContribution(f, v, w, True) for f, v in scored)
    return CompositeResult(
        model_id=spec.model_id, model_version=spec.version,
        methodology_status="experimental",
        country_iso3=country_iso3, scoring_period=scoring_period,
        score=sum(v * w for _, v, w in
                  ((c.force_code, c.value, c.weight) for c in contribs)),
        included_forces=tuple(c.force_code for c in contribs),
        excluded_forces=tuple(excluded),
        missing_forces=(),
        weights={c.force_code: c.weight for c in contribs},
        coverage_ratio=1.0,
        contributions=contribs,
        warnings=_warn_weights(spec, n, 0),
        limitations=(
            "Fixed subset maximizes comparability at the cost of breadth",
        ),
    )


# --- Registry of experimental composite models --------------------------------

_ALL_LEVEL_FORCES = frozenset(
    {
        "rule_of_law", "corruption", "internal_conflict",
        "leadership_capabilities", "education",
        "wealth_opportunity_values_gaps", "indebtedness",
        "productivity_output_growth", "character_determination",
    }
)
# Fixed comparable subset: forces available across ALL 8 tracked countries
# (education/OECD percentile lack CHN/IND coverage).
_COMPARABLE_SUBSET = frozenset(
    {
        "rule_of_law", "corruption", "internal_conflict",
        "leadership_capabilities", "wealth_opportunity_values_gaps",
        "indebtedness", "character_determination",
    }
)

COMPOSITE_MODELS: dict[str, CompositeModelSpec] = {
    "model_a_equal": CompositeModelSpec(
        model_id="model_a_equal", version="v1", kind="equal",
        eligible_forces=_ALL_LEVEL_FORCES,
        missing_policy=MissingPolicy.MIN_COVERAGE, min_coverage=0.5,
        notes="equal-force benchmark — reference only",
    ),
    "model_b_domain": CompositeModelSpec(
        model_id="model_b_domain", version="v1", kind="domain",
        eligible_forces=_ALL_LEVEL_FORCES,
        missing_policy=MissingPolicy.MIN_COVERAGE, min_coverage=0.5,
        notes="equal weight per populated domain",
    ),
    "model_c_overlap": CompositeModelSpec(
        model_id="model_c_overlap", version="v1", kind="overlap_adjusted",
        eligible_forces=_ALL_LEVEL_FORCES,
        missing_policy=MissingPolicy.MIN_COVERAGE, min_coverage=0.5,
        notes="declared overlap groups share one weight",
    ),
    "model_d_comparable": CompositeModelSpec(
        model_id="model_d_comparable", version="v1", kind="fixed_subset",
        eligible_forces=_COMPARABLE_SUBSET,
        missing_policy=MissingPolicy.STRICT,
        notes="forces present in all 8 tracked countries",
    ),
}

_EXECUTORS = {
    "equal": model_a_equal,
    "domain": model_b_domain,
    "overlap_adjusted": model_c_overlap_adjusted,
    "fixed_subset": model_d_fixed_subset,
}


def run_composite(
    model_id: str,
    signals: dict[str, ForceSignal],
    country_iso3: str,
    scoring_period: str,
) -> CompositeResult:
    spec = COMPOSITE_MODELS.get(model_id)
    if spec is None:
        raise KeyError(f"unknown composite model {model_id!r}")
    return _EXECUTORS[spec.kind](spec, signals, country_iso3, scoring_period)
