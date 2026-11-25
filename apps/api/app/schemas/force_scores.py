"""Response schema for the read-only force-scores endpoint.

ForceScores are DERIVED, non-persisted signals (Sprint 5.22+). This schema
only publishes what the aggregation layer already computes — never an
invented number. Unscored forces are explicit: level_score = None with
execution_status "deferred", never 0.
"""

from typing import Optional

from pydantic import BaseModel


class ForceScoreRead(BaseModel):
    force_code: str
    force_name: str
    # "scored" when a numeric level exists; "deferred" when approved
    # aggregation has not (yet) produced a number.
    execution_status: str
    level_score: Optional[float] = None
    relative_score: Optional[float] = None
    momentum_score: Optional[float] = None
    confidence: Optional[float] = None
    coverage_status: str
    period: str
    model_version: str
    limitations: list[str]
    reasons: list[str]
    backtest_safe: bool


class ForceScoresResponse(BaseModel):
    country: str
    normalization_version: str
    force_aggregation_version: str
    forces: list[ForceScoreRead]


class ForceHistoryPoint(BaseModel):
    """One scoring period in a force's history."""

    period: str
    execution_status: str
    level_score: Optional[float] = None
    relative_score: Optional[float] = None
    momentum_score: Optional[float] = None
    coverage_status: str
    missing_components: list[str]


class ForceHistoryResponse(BaseModel):
    """Retrospective force history — computed from latest vintages.

    This is RETROSPECTIVE descriptive analysis, not a release-date-safe
    backtest (backtest_safe=False): each point uses the latest stored
    vintage, so revisions that arrived later are visible in earlier
    periods' inputs.
    """

    country: str
    force_code: str
    force_name: str
    retrospective: bool = True
    backtest_safe: bool = False
    # How inputs were selected (Mission 4 §23): retrospective latest-vintage
    # by default; strict_as_of / research_assumption only on explicit request.
    execution_mode: str = "retrospective_latest_vintage"
    info_cutoff: Optional[str] = None
    model_version: str
    points: list[ForceHistoryPoint]


class UncertaintyIndicatorRead(BaseModel):
    """Published provider uncertainty for one indicator at a source period.

    Only REAL provider-published diagnostics are returned — never invented
    confidence percentages. Missing kinds stay null.
    """

    indicator_code: str
    source_period: str
    ci_lower_bound: Optional[float] = None
    ci_upper_bound: Optional[float] = None
    source_count: Optional[float] = None


class CountryUncertaintyResponse(BaseModel):
    """All available published uncertainty diagnostics for a country."""

    country: str
    indicators: list[UncertaintyIndicatorRead]


class UncertaintyPoint(BaseModel):
    """Published provider diagnostics for ONE source period.

    Every field is provider-published (WGI 90% CI bounds, source count).
    Periods without published diagnostics are ABSENT — never interpolated.
    """

    period_start: str
    ci_lower_bound: Optional[float] = None
    ci_upper_bound: Optional[float] = None
    source_count: Optional[float] = None


class IndicatorUncertaintyHistory(BaseModel):
    """Full published uncertainty history for one indicator."""

    country: str
    indicator_code: str
    points: list[UncertaintyPoint]
