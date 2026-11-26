"""Scientific research-foundation persistence.

These tables are deliberately separate from the production Observation path:
they store independently defined outcomes, source-release/vintage evidence,
research-population eligibility, registered protocols, append-only predictions
and evaluation results. No table here participates in force scoring.
"""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ResearchObservation(Base):
    """Source-versioned research observation (JST, ALFRED, archived releases)."""

    __tablename__ = "research_observations"
    __table_args__ = (
        UniqueConstraint(
            "source_key", "dataset_version", "entity_code", "variable_code",
            "period_start", "vintage_date", name="uq_research_obs_identity",
        ),
        Index("ix_research_obs_entity_var_period", "entity_code", "variable_code", "period_start"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(80), index=True)
    dataset_version: Mapped[str] = mapped_column(String(80), index=True)
    entity_code: Mapped[str] = mapped_column(String(40), index=True)
    entity_name: Mapped[Optional[str]] = mapped_column(String(160))
    entity_type: Mapped[str] = mapped_column(String(40), default="country")
    variable_code: Mapped[str] = mapped_column(String(100), index=True)
    variable_name: Mapped[Optional[str]] = mapped_column(String(255))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    value: Mapped[float] = mapped_column()
    unit: Mapped[Optional[str]] = mapped_column(String(120))
    vintage_date: Mapped[Optional[date]] = mapped_column(Date, index=True)
    release_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), index=True)
    release_evidence_type: Mapped[str] = mapped_column(String(60), default="dataset_release")
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    source_version: Mapped[Optional[str]] = mapped_column(String(120))
    source_url: Mapped[Optional[str]] = mapped_column(String(500))
    license_code: Mapped[Optional[str]] = mapped_column(String(80))
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrisisEvent(Base):
    """Independent source-defined crisis/outcome event."""

    __tablename__ = "crisis_events"
    __table_args__ = (
        UniqueConstraint(
            "source_key", "dataset_version", "source_event_key", "revision_number",
            name="uq_crisis_event_revision",
        ),
        Index("ix_crisis_events_entity_type_start", "entity_code", "event_type", "start_period"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(80), index=True)
    dataset_version: Mapped[str] = mapped_column(String(80), index=True)
    source_event_key: Mapped[str] = mapped_column(String(255), index=True)
    revision_number: Mapped[int] = mapped_column(default=1)
    supersedes_event_id: Mapped[Optional[int]] = mapped_column(ForeignKey("crisis_events.id"))
    entity_code: Mapped[str] = mapped_column(String(40), index=True)
    entity_name: Mapped[Optional[str]] = mapped_column(String(160))
    entity_type: Mapped[str] = mapped_column(String(40), default="country")
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    event_state: Mapped[str] = mapped_column(String(40), default="onset")
    classification: Mapped[Optional[str]] = mapped_column(String(80))
    start_period: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_period: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    dating_precision: Mapped[str] = mapped_column(String(40), default="annual")
    coverage_scope: Mapped[Optional[str]] = mapped_column(String(160))
    source_definition: Mapped[Optional[str]] = mapped_column(Text)
    source_conflicts: Mapped[Optional[dict]] = mapped_column(JSON)
    publication_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_reference: Mapped[Optional[str]] = mapped_column(String(500))
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    checksum: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CrisisCoverage(Base):
    """Evidence that a source covers an entity-period even when no event exists."""

    __tablename__ = "crisis_coverage"
    __table_args__ = (
        UniqueConstraint(
            "source_key", "dataset_version", "entity_code", "event_type",
            "period_start", name="uq_crisis_coverage_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(80), index=True)
    dataset_version: Mapped[str] = mapped_column(String(80), index=True)
    entity_code: Mapped[str] = mapped_column(String(40), index=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    coverage_status: Mapped[str] = mapped_column(String(60), default="covered")
    variable_code: Mapped[Optional[str]] = mapped_column(String(100))
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TheoryRegistryEntry(Base):
    __tablename__ = "theory_registry"
    __table_args__ = (UniqueConstraint("theory_code", "version", name="uq_theory_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    theory_code: Mapped[str] = mapped_column(String(100), index=True)
    version: Mapped[str] = mapped_column(String(40))
    source_title: Mapped[str] = mapped_column(String(255))
    source_author: Mapped[Optional[str]] = mapped_column(String(160))
    source_edition: Mapped[Optional[str]] = mapped_column(String(120))
    chapter_section: Mapped[Optional[str]] = mapped_column(String(160))
    publication_date: Mapped[Optional[date]] = mapped_column(Date)
    concept: Mapped[str] = mapped_column(Text)
    atlas_interpretation: Mapped[str] = mapped_column(Text)
    framework_differences: Mapped[Optional[str]] = mapped_column(Text)
    measurement_limitations: Mapped[Optional[str]] = mapped_column(Text)
    framework_scope: Mapped[str] = mapped_column(String(80), index=True)
    atlas_operational: Mapped[bool] = mapped_column(Boolean, default=False)
    testable_status: Mapped[str] = mapped_column(String(80), default="insufficient_evidence")
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    content_checksum: Mapped[str] = mapped_column(String(64), index=True)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HypothesisProtocol(Base):
    __tablename__ = "hypothesis_protocols"
    __table_args__ = (UniqueConstraint("hypothesis_code", "protocol_version", name="uq_hypothesis_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    hypothesis_code: Mapped[str] = mapped_column(String(40), index=True)
    protocol_version: Mapped[str] = mapped_column(String(40))
    protocol_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(255))
    definition: Mapped[str] = mapped_column(Text)
    scientific_rationale: Mapped[str] = mapped_column(Text)
    target_outcome: Mapped[str] = mapped_column(Text)
    research_population: Mapped[dict] = mapped_column(JSON)
    predictor_variables: Mapped[dict] = mapped_column(JSON)
    information_cutoff_rules: Mapped[dict] = mapped_column(JSON)
    forecast_horizons: Mapped[dict] = mapped_column(JSON)
    measurement_method: Mapped[dict] = mapped_column(JSON)
    training_periods: Mapped[dict] = mapped_column(JSON)
    validation_periods: Mapped[dict] = mapped_column(JSON)
    test_population: Mapped[dict] = mapped_column(JSON)
    evaluation_metrics: Mapped[dict] = mapped_column(JSON)
    minimum_evidence: Mapped[dict] = mapped_column(JSON)
    falsification_criteria: Mapped[str] = mapped_column(Text)
    known_limitations: Mapped[dict] = mapped_column(JSON)
    protocol_status: Mapped[str] = mapped_column(String(80), default="retrospective")
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    content_checksum: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PredictionLedgerEntry(Base):
    __tablename__ = "prediction_ledger"
    __table_args__ = (
        UniqueConstraint("prediction_key", name="uq_prediction_key"),
        Index("ix_prediction_hypothesis_origin", "hypothesis_code", "entity_code", "forecast_origin"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_key: Mapped[str] = mapped_column(String(255), index=True)
    hypothesis_code: Mapped[str] = mapped_column(String(40), index=True)
    protocol_version: Mapped[str] = mapped_column(String(40), index=True)
    model_id: Mapped[str] = mapped_column(String(100), index=True)
    model_version: Mapped[str] = mapped_column(String(80))
    entity_code: Mapped[str] = mapped_column(String(40), index=True)
    entity_type: Mapped[str] = mapped_column(String(40), default="country")
    forecast_origin: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    info_cutoff: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    horizon_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    horizon_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    target_outcome: Mapped[str] = mapped_column(String(120), index=True)
    prediction_status: Mapped[str] = mapped_column(String(80), default="available")
    unavailable_reason: Mapped[Optional[str]] = mapped_column(Text)
    prediction_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    uncertainty_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    data_coverage: Mapped[dict] = mapped_column(JSON)
    input_vintage_ids: Mapped[dict] = mapped_column(JSON)
    dataset_versions: Mapped[dict] = mapped_column(JSON)
    evaluation_status: Mapped[str] = mapped_column(String(80), default="pending")
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    content_checksum: Mapped[str] = mapped_column(String(64), index=True)


class PredictionOutcome(Base):
    __tablename__ = "prediction_outcomes"
    __table_args__ = (UniqueConstraint("prediction_id", "outcome_source_key", name="uq_prediction_outcome_source"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    prediction_id: Mapped[int] = mapped_column(ForeignKey("prediction_ledger.id"), index=True)
    outcome_source_key: Mapped[str] = mapped_column(String(80), index=True)
    outcome_status: Mapped[str] = mapped_column(String(80), index=True)
    outcome_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    outcome_checksum: Mapped[str] = mapped_column(String(64), index=True)


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (UniqueConstraint("evaluation_key", name="uq_evaluation_key"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_key: Mapped[str] = mapped_column(String(255), index=True)
    hypothesis_code: Mapped[str] = mapped_column(String(40), index=True)
    protocol_version: Mapped[str] = mapped_column(String(40), index=True)
    model_id: Mapped[str] = mapped_column(String(100), index=True)
    model_version: Mapped[str] = mapped_column(String(80))
    evaluation_type: Mapped[str] = mapped_column(String(80), index=True)
    result_state: Mapped[str] = mapped_column(String(100), index=True)
    sample_counts: Mapped[dict] = mapped_column(JSON)
    metrics: Mapped[dict] = mapped_column(JSON)
    evidence_cutoff: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    execution_mode: Mapped[str] = mapped_column(String(80))
    dataset_versions: Mapped[dict] = mapped_column(JSON)
    limitations: Mapped[dict] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    content_checksum: Mapped[str] = mapped_column(String(64), index=True)


class ResearchPopulationMembership(Base):
    __tablename__ = "research_population_memberships"
    __table_args__ = (UniqueConstraint("population_code", "population_version", "entity_code", name="uq_population_member"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    population_code: Mapped[str] = mapped_column(String(100), index=True)
    population_version: Mapped[str] = mapped_column(String(40), index=True)
    entity_code: Mapped[str] = mapped_column(String(40), index=True)
    entity_name: Mapped[str] = mapped_column(String(160))
    entity_type: Mapped[str] = mapped_column(String(40), default="country")
    eligibility_rule: Mapped[str] = mapped_column(Text)
    eligibility_status: Mapped[str] = mapped_column(String(80), default="eligible")
    inclusion_reason: Mapped[Optional[str]] = mapped_column(Text)
    source_requirements: Mapped[dict] = mapped_column(JSON)
    achieved_coverage: Mapped[dict] = mapped_column(JSON)
    limitations: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DatasetRightsRegistry(Base):
    __tablename__ = "dataset_rights"
    __table_args__ = (UniqueConstraint("source_key", "dataset_version", name="uq_dataset_rights"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(80), index=True)
    dataset_version: Mapped[str] = mapped_column(String(80), index=True)
    license_code: Mapped[Optional[str]] = mapped_column(String(120))
    attribution_required: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_redistribution: Mapped[str] = mapped_column(String(80), default="review_required")
    derived_publication: Mapped[str] = mapped_column(String(80), default="review_required")
    commercial_use: Mapped[str] = mapped_column(String(80), default="review_required")
    share_alike: Mapped[bool] = mapped_column(Boolean, default=False)
    publication_status: Mapped[str] = mapped_column(String(80), default="restricted_pending_review")
    rights_reference: Mapped[Optional[str]] = mapped_column(String(500))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvidenceStatusEntry(Base):
    __tablename__ = "evidence_status_registry"
    __table_args__ = (UniqueConstraint("subject_type", "subject_key", "evidence_version", name="uq_evidence_subject"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(80), index=True)
    subject_key: Mapped[str] = mapped_column(String(160), index=True)
    evidence_version: Mapped[str] = mapped_column(String(40))
    evidence_status: Mapped[str] = mapped_column(String(100), index=True)
    methodology_status: Mapped[str] = mapped_column(String(80), default="experimental")
    source_versions: Mapped[dict] = mapped_column(JSON)
    evaluation_versions: Mapped[Optional[dict]] = mapped_column(JSON)
    limitations: Mapped[dict] = mapped_column(JSON)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ValidationQuestion(Base):
    """Versioned canonical Big Cycle validation question."""

    __tablename__ = "validation_questions"
    __table_args__ = (
        UniqueConstraint("question_code", "registry_version", name="uq_validation_question_version"),
        Index("ix_validation_questions_category_status", "category", "implementation_status", "research_validation_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    question_code: Mapped[str] = mapped_column(String(12), index=True)
    registry_version: Mapped[str] = mapped_column(String(40), index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    original_question: Mapped[str] = mapped_column(Text)
    short_title: Mapped[str] = mapped_column(String(120), index=True)
    theory_claims: Mapped[dict] = mapped_column(JSON)
    related_forces: Mapped[dict] = mapped_column(JSON)
    related_power_measures: Mapped[dict] = mapped_column(JSON)
    required_datasets: Mapped[dict] = mapped_column(JSON)
    available_datasets: Mapped[dict] = mapped_column(JSON)
    missing_datasets: Mapped[dict] = mapped_column(JSON)
    historical_coverage: Mapped[dict] = mapped_column(JSON)
    country_coverage: Mapped[dict] = mapped_column(JSON)
    existing_research_methods: Mapped[dict] = mapped_column(JSON)
    supporting_evidence: Mapped[dict] = mapped_column(JSON)
    contradictory_evidence: Mapped[dict] = mapped_column(JSON)
    alternative_explanations: Mapped[dict] = mapped_column(JSON)
    falsification_criteria: Mapped[str] = mapped_column(Text)
    scientific_limitations: Mapped[dict] = mapped_column(JSON)
    source_references: Mapped[dict] = mapped_column(JSON)
    implementation_status: Mapped[str] = mapped_column(String(80), index=True)
    research_validation_status: Mapped[str] = mapped_column(String(100), index=True)
    current_answer: Mapped[str] = mapped_column(Text)
    related_hypotheses: Mapped[dict] = mapped_column(JSON)
    chart: Mapped[Optional[dict]] = mapped_column(JSON)
    previous_implementation_status: Mapped[str] = mapped_column(String(80), default="unavailable_prior_assessment")
    last_reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    methodology_version: Mapped[str] = mapped_column(String(80))
    content_checksum: Mapped[str] = mapped_column(String(64), index=True)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@event.listens_for(PredictionLedgerEntry, "before_update", propagate=True)
def _reject_prediction_update(mapper, connection, target):  # pragma: no cover
    raise ValueError("prediction_ledger is append-only; record a new prediction instead")


@event.listens_for(PredictionOutcome, "before_update", propagate=True)
def _reject_outcome_update(mapper, connection, target):  # pragma: no cover
    raise ValueError("prediction_outcomes is append-only; insert a corrected outcome")


@event.listens_for(EvaluationResult, "before_update", propagate=True)
def _reject_evaluation_update(mapper, connection, target):  # pragma: no cover
    raise ValueError("evaluation_results is append-only; register a new evaluation")


@event.listens_for(HypothesisProtocol, "before_update", propagate=True)
def _reject_protocol_update(mapper, connection, target):  # pragma: no cover
    raise ValueError("hypothesis protocol versions are immutable; register a new version")


@event.listens_for(TheoryRegistryEntry, "before_update", propagate=True)
def _reject_theory_update(mapper, connection, target):  # pragma: no cover
    raise ValueError("theory registry versions are immutable; register a new version")


@event.listens_for(PredictionLedgerEntry, "before_delete", propagate=True)
def _reject_prediction_delete(mapper, connection, target):  # pragma: no cover
    raise ValueError("prediction_ledger is append-only; failed predictions are preserved")


@event.listens_for(PredictionOutcome, "before_delete", propagate=True)
def _reject_outcome_delete(mapper, connection, target):  # pragma: no cover
    raise ValueError("prediction_outcomes is append-only; insert a corrected outcome")


@event.listens_for(EvaluationResult, "before_delete", propagate=True)
def _reject_evaluation_delete(mapper, connection, target):  # pragma: no cover
    raise ValueError("evaluation_results is append-only; register a new evaluation")


@event.listens_for(HypothesisProtocol, "before_delete", propagate=True)
def _reject_protocol_delete(mapper, connection, target):  # pragma: no cover
    raise ValueError("hypothesis protocol versions are immutable")


@event.listens_for(TheoryRegistryEntry, "before_delete", propagate=True)
def _reject_theory_delete(mapper, connection, target):  # pragma: no cover
    raise ValueError("theory registry versions are immutable")


@event.listens_for(ValidationQuestion, "before_update", propagate=True)
def _reject_validation_question_update(mapper, connection, target):  # pragma: no cover
    raise ValueError("validation question versions are immutable; register a new version")


@event.listens_for(ValidationQuestion, "before_delete", propagate=True)
def _reject_validation_question_delete(mapper, connection, target):  # pragma: no cover
    raise ValueError("validation question versions are immutable")
