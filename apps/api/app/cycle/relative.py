"""Cross-sectional relative scoring — Sprint 5.8 (DEC-017, WGI x3 only).

relative_score answers ONE question: "Where does this country rank on this
indicator within the comparison universe (tracked_8) at the SAME scoring
snapshot?" It is the country's relative position within tracked_8 — NEVER a
global percentile, a world ranking, or a Big Cycle phase. level_score keeps
its own meaning (for WGI, the provider's absolute 0-100 scale) and is never
re-scaled or replaced.

Formula (versioned MODEL CHOICE, DEC-017): mid-rank plotting position

    relative_score = 100 * (average_rank - 0.5) / n

with rank 1 = weakest and rank n = strongest (higher WGI = stronger, no
inversion). Ties use the AVERAGE rank, so tied members receive identical
scores — never broken by ISO code, row id, or query order; the computation is
deterministic and input-order independent. For n=8 the possible scores are
6.25 / 18.75 / 31.25 / 43.75 / 56.25 / 68.75 / 81.25 / 93.75 — the strongest
of only 8 countries is not mislabeled 100 and the weakest is not mislabeled 0.

Rules inherited from the alignment layer (DEC-015 / ISSUE-004):

- Every member is aligned with align_observation_as_of at the SAME scoring
  period — country scoping, latest vintage, period-complete eligibility, and
  no-future-leakage all apply. Never "latest overall".
- A stale-but-still-usable observation may participate; an unusable one may
  NOT. Freshness gates usability only — it NEVER scales relative_score.
- Every participating value must be within [0, 100]; out-of-range is a DATA
  ERROR (raised, never clamped, never treated as missing, never ranked).
- COMPLETE-UNIVERSE RULE: tracked_8 requires all 8 members usable. 7/8 ->
  no relative score for ANYONE (never a seven-country score still called
  tracked_8), with the usable/expected counts carried as provenance. Missing
  members never become zero.

Relative scoring is independent from momentum: a relative score may exist
when momentum is None (insufficient own-history), and vice versa.
"""
from dataclasses import dataclass
from typing import Mapping, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.cycle.freshness import (
    DEFAULT_FRESHNESS_POLICIES,
    FreshnessPolicy,
    evaluate_freshness,
    own_period_age,
)
from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    AlignedValue,
    NormalizationDataError,
    NormalizationFamily,
    NormalizationNotImplementedError,
    ReferenceUniverseSpec,
    get_normalization_spec,
)
from app.services.alignment_service import align_observation_as_of


@dataclass(frozen=True)
class RelativeMember:
    """One usable universe member's ranked position at the snapshot."""

    country_iso3: str
    value: float
    rank: float  # average (mid) rank, 1 = weakest, n = strongest
    relative_score: float  # 100 * (rank - 0.5) / n
    source_period: str


@dataclass(frozen=True)
class RelativeCrossSection:
    """The tracked_8 cross-section at one (indicator, scoring period).

    When is_complete is False, members is EMPTY and no member received a
    score — the usable/expected counts explain why. Unusable members are
    never scored, never zero-filled, and never dropped from the count.
    """

    universe_id: str
    expected_n: int
    usable_n: int
    is_complete: bool
    members: tuple[RelativeMember, ...]

    def member_for(self, country_iso3: str) -> Optional[RelativeMember]:
        for member in self.members:
            if member.country_iso3 == country_iso3:
                return member
        return None


def mid_rank_relative_scores(
    values: Mapping[str, float],
) -> dict[str, tuple[float, float]]:
    """Average (mid) ranks and plotting-position relative scores, higher = stronger.

    Returns {member: (average_rank, relative_score)} where
    relative_score = 100 * (average_rank - 0.5) / n. Ties share the average
    of the tied positions; the result is identical for any input ordering.
    Pure function — no DB access, no persistence.
    """
    if not values:
        raise ValueError("mid_rank_relative_scores requires at least one value")
    n = len(values)
    ordered = sorted(values.items(), key=lambda item: item[1])  # ascending: weakest first
    results: dict[str, tuple[float, float]] = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and ordered[j + 1][1] == ordered[i][1]:
            j += 1
        # Tied members (positions i+1 .. j+1, 1-based) share the average rank.
        average_rank = (i + 1 + j + 1) / 2.0
        relative_score = 100.0 * (average_rank - 0.5) / n
        for k in range(i, j + 1):
            results[ordered[k][0]] = (average_rank, relative_score)
        i = j + 1
    return results


async def build_relative_cross_section(
    session: AsyncSession,
    indicator_code: str,
    scoring_period,
    universe: ReferenceUniverseSpec,
    freshness_policy: FreshnessPolicy | None = None,
    approved_indicators: frozenset[str] | None = None,
) -> RelativeCrossSection:
    """Align every universe member at the SAME scoring period and rank them.

    Every member goes through align_observation_as_of (never a "latest
    overall" query), so country scoping, latest-vintage selection, DEC-015
    period-complete eligibility, and no-future-leakage are all inherited.
    Read-only: nothing is persisted, raw observations are never touched.

    Execution gate (Sprint 6.4 hardening): the indicator must have level
    family DIRECT_0_100, relative family CROSS_SECTIONAL_RELATIVE, AND be
    in the explicit approved-indicator set. The approved set defaults to
    CURRENT_MODEL_VERSION.direct_relative_approved_indicators (the WGI x3
    for v0.7). A direct call for any other indicator — including
    TERTIARY_ATTAINMENT_25_34, which is DIRECT_0_100 +
    CROSS_SECTIONAL_RELATIVE but NOT approved (DEC-032) — raises
    NormalizationNotImplementedError instead of silently ranking it. A
    registry family declaration alone NEVER enables a dimension.
    """
    spec = get_normalization_spec(indicator_code)
    if not (
        spec.level_family is NormalizationFamily.direct_0_100
        and spec.relative_family is NormalizationFamily.cross_sectional_relative
    ):
        raise NormalizationNotImplementedError(
            f"{indicator_code}: relative scoring requires level DIRECT_0_100 + "
            f"relative CROSS_SECTIONAL_RELATIVE (got {spec.level_family.value} "
            f"+ {spec.relative_family.value if spec.relative_family else None}) — "
            "approved for the WGI x3 only"
        )
    approved = approved_indicators
    if approved is None:
        approved = CURRENT_MODEL_VERSION.direct_relative_approved_indicators
    if indicator_code not in approved:
        raise NormalizationNotImplementedError(
            f"{indicator_code}: relative scoring is not approved in the "
            f"current model version ({CURRENT_MODEL_VERSION.version_id!r}) — "
            f"approved indicators: {sorted(approved)}"
        )
    policy = freshness_policy or DEFAULT_FRESHNESS_POLICIES[spec.freshness_class]

    usable: dict[str, AlignedValue] = {}
    for iso3 in universe.members:
        aligned = await align_observation_as_of(
            session, iso3, indicator_code, scoring_period
        )
        if aligned is None:
            continue  # no eligible observation — member unusable, never zero
        freshness = evaluate_freshness(
            own_period_age(aligned.age_periods, spec.freshness_class), policy
        )
        if not freshness.is_usable:
            continue  # too stale — member unusable, never zero
        if not 0.0 <= aligned.raw_value <= 100.0:
            raise NormalizationDataError(
                f"{indicator_code} for {iso3} at source period "
                f"{aligned.source_period}: relative scoring requires a "
                f"provider value in [0, 100], got {aligned.raw_value} — "
                "refusing to clamp, rank, or treat as missing"
            )
        usable[iso3] = aligned

    expected_n = len(universe.members)
    usable_n = len(usable)
    if usable_n != expected_n:
        # COMPLETE-UNIVERSE RULE (DEC-017): a partial cross-section is never
        # scored as tracked_8 — no member receives a score.
        return RelativeCrossSection(
            universe_id=universe.id,
            expected_n=expected_n,
            usable_n=usable_n,
            is_complete=False,
            members=(),
        )

    ranked = mid_rank_relative_scores(
        {iso3: aligned.raw_value for iso3, aligned in usable.items()}
    )
    members = tuple(
        sorted(
            (
                RelativeMember(
                    country_iso3=iso3,
                    value=aligned.raw_value,
                    rank=ranked[iso3][0],
                    relative_score=ranked[iso3][1],
                    source_period=aligned.source_period,
                )
                for iso3, aligned in usable.items()
            ),
            key=lambda member: member.country_iso3,
        )
    )
    return RelativeCrossSection(
        universe_id=universe.id,
        expected_n=expected_n,
        usable_n=usable_n,
        is_complete=True,
        members=members,
    )