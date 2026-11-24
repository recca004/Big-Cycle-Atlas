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
