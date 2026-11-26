"""Read-side summaries for the canonical validation-question registry."""
from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Country, CrisisCoverage, CrisisEvent, DataSource, Indicator,
    Observation, ResearchObservation, ResearchPopulationMembership,
    SourceSeries, ValidationQuestion,
)
from app.research.validation_questions import VALIDATION_REGISTRY_VERSION

PRODUCTION_SOURCES = {"world_bank", "bis", "imf", "oecd", "wid"}
RESEARCH_SOURCES = {
    "jst_macrohistory", "imf_cofer", "bis_fx_turnover", "bis_lbs",
    "bis_credit_policy", "pwt", "maddison",
}
REGISTRY_SOURCES = {
    "theory_registry", "hypothesis_protocols", "power_registry",
    "currency_research_entities", "atlas_cycle_model", "atlas_force_engine",
    "primary_observatory_v1", "jst_extended_research_v1",
    "research_population", "crisis_registry",
}


def _date(value: Any) -> str | None:
    return value.date().isoformat() if value else None


def question_payload(row: ValidationQuestion, *, details: bool = True) -> dict[str, Any]:
    base = {
        "question_code": row.question_code,
        "registry_version": row.registry_version,
        "category": row.category,
        "original_question": row.original_question,
        "short_title": row.short_title,
        "implementation_status": row.implementation_status,
        "research_validation_status": row.research_validation_status,
        "current_answer": row.current_answer,
        "previous_implementation_status": row.previous_implementation_status,
        "last_reviewed_at": _date(row.last_reviewed_at),
        "methodology_version": row.methodology_version,
        "related_hypotheses": row.related_hypotheses,
        "related_forces": row.related_forces,
        "related_power_measures": row.related_power_measures,
    }
    if details:
        base.update({
            "theory_claims": row.theory_claims,
            "required_datasets": row.required_datasets,
            "available_datasets": row.available_datasets,
            "missing_datasets": row.missing_datasets,
            "historical_coverage": row.historical_coverage,
            "country_coverage": row.country_coverage,
            "existing_research_methods": row.existing_research_methods,
            "supporting_evidence": row.supporting_evidence,
            "contradictory_evidence": row.contradictory_evidence,
            "alternative_explanations": row.alternative_explanations,
            "falsification_criteria": row.falsification_criteria,
            "scientific_limitations": row.scientific_limitations,
            "source_references": row.source_references,
            "chart": row.chart,
            "content_checksum": row.content_checksum,
        })
    return base


async def _production_evidence(session: AsyncSession, dataset: dict[str, Any]) -> list[dict[str, Any]]:
    source_key = dataset.get("source_key")
    indicators = set(dataset.get("indicators") or [])
    stmt = (
        select(
            DataSource.key, Indicator.code, func.count(Observation.id),
            func.count(func.distinct(Observation.country_id)),
            func.min(Observation.period_start), func.max(Observation.period_start),
        )
        .select_from(Observation)
        .join(DataSource, DataSource.id == Observation.data_source_id)
        .join(Indicator, Indicator.id == Observation.indicator_id)
        .where(DataSource.key == source_key)
        .group_by(DataSource.key, Indicator.code)
        .order_by(Indicator.code)
    )
    rows = (await session.execute(stmt)).all()
    result = []
    for source, code, count, countries, first, last in rows:
        if indicators and code not in indicators:
            continue
        result.append({
            "source_key": source, "indicator_code": code, "observations": count,
            "entities": countries, "earliest_period": _date(first), "latest_period": _date(last),
        })
    return result


async def _research_evidence(session: AsyncSession, dataset: dict[str, Any]) -> list[dict[str, Any]]:
    source_key = dataset.get("source_key")
    dataset_version = dataset.get("dataset_version") or dataset.get("dataset")
    variables = set(dataset.get("variables") or [])
    stmt = (
        select(
            ResearchObservation.source_key, ResearchObservation.dataset_version,
            ResearchObservation.variable_code, func.count(ResearchObservation.id),
            func.count(func.distinct(ResearchObservation.entity_code)),
            func.min(ResearchObservation.period_start), func.max(ResearchObservation.period_start),
        )
        .where(ResearchObservation.source_key == source_key)
        .group_by(
            ResearchObservation.source_key, ResearchObservation.dataset_version,
            ResearchObservation.variable_code,
        )
        .order_by(ResearchObservation.variable_code)
    )
    if dataset_version and dataset_version not in {
        "R6", "COFER-SDMX-2.1", "WS_DER_OTC_TOV", "WS_LBS_D_PUB", "WS_TC_CBPOL", "11.0", "2023",
        "current WDI import", "current WEO import", "current BIS import", "current OECD import", "current WID import",
    }:
        stmt = stmt.where(ResearchObservation.dataset_version == dataset_version)
    rows = (await session.execute(stmt)).all()
    return [
        {
            "source_key": source, "dataset_version": version, "variable_code": variable,
            "observations": count, "entities": entities,
            "earliest_period": _date(first), "latest_period": _date(last),
        }
        for source, version, variable, count, entities, first, last in rows
        if not variables or variable in variables
    ]


async def _crisis_evidence(session: AsyncSession) -> list[dict[str, Any]]:
    event_rows = (await session.execute(select(
        CrisisEvent.source_key, CrisisEvent.dataset_version, CrisisEvent.event_type,
        func.count(CrisisEvent.id), func.count(func.distinct(CrisisEvent.entity_code)),
        func.min(CrisisEvent.start_period), func.max(CrisisEvent.start_period),
    ).group_by(
        CrisisEvent.source_key, CrisisEvent.dataset_version, CrisisEvent.event_type,
    ))).all()
    coverage_rows = (await session.execute(select(
        CrisisCoverage.source_key, CrisisCoverage.dataset_version,
        CrisisCoverage.event_type, func.count(CrisisCoverage.id),
        func.count(func.distinct(CrisisCoverage.entity_code)),
    ).group_by(
        CrisisCoverage.source_key, CrisisCoverage.dataset_version,
        CrisisCoverage.event_type,
    ))).all()
    return [
        {
            "source_key": source, "dataset_version": version, "event_type": event_type,
            "events": count, "entities": entities,
            "earliest_period": _date(first), "latest_period": _date(last),
        }
        for source, version, event_type, count, entities, first, last in event_rows
    ] + [
        {
            "source_key": source, "dataset_version": version, "event_type": event_type,
            "coverage_rows": count, "entities": entities,
        }
        for source, version, event_type, count, entities in coverage_rows
    ]


async def _population_evidence(session: AsyncSession, source_key: str) -> list[dict[str, Any]]:
    if source_key == "research_population":
        stmt = select(
            ResearchPopulationMembership.population_code,
            ResearchPopulationMembership.population_version,
            func.count(ResearchPopulationMembership.id),
        ).group_by(
            ResearchPopulationMembership.population_code,
            ResearchPopulationMembership.population_version,
        )
    else:
        stmt = select(
            ResearchPopulationMembership.population_code,
            ResearchPopulationMembership.population_version,
            func.count(ResearchPopulationMembership.id),
        ).where(ResearchPopulationMembership.population_code == source_key).group_by(
            ResearchPopulationMembership.population_code,
            ResearchPopulationMembership.population_version,
        )
    return [
        {"population_code": code, "population_version": version, "memberships": count}
        for code, version, count in (await session.execute(stmt)).all()
    ]


async def actual_evidence(session: AsyncSession, question: ValidationQuestion) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    for dataset in question.available_datasets:
        source_key = dataset.get("source_key")
        record = {"declared_dataset": dataset}
        if source_key in PRODUCTION_SOURCES:
            rows = await _production_evidence(session, dataset)
        elif source_key in RESEARCH_SOURCES:
            rows = await _research_evidence(session, dataset)
        elif source_key == "crisis_registry":
            rows = await _crisis_evidence(session)
        elif source_key in {"primary_observatory_v1", "jst_extended_research_v1", "research_population"}:
            rows = await _population_evidence(session, source_key)
        elif source_key in REGISTRY_SOURCES:
            rows = [{"registry_subject": source_key, "status": "available_metadata"}]
        else:
            rows = []
        record["observed"] = rows
        evidence.append(record)
    return evidence


async def chart_points(session: AsyncSession, question: ValidationQuestion, entity: str | None = None) -> dict[str, Any] | None:
    chart = question.chart
    if not chart:
        return None
    entity_code = (entity or chart.get("entity_code") or "USA").upper()
    if chart.get("kind") == "research_observation":
        stmt = (
            select(ResearchObservation.period_start, ResearchObservation.value, ResearchObservation.unit)
            .where(
                ResearchObservation.source_key == chart.get("source_key"),
                ResearchObservation.dataset_version == chart.get("dataset_version"),
                ResearchObservation.entity_code == entity_code,
                ResearchObservation.variable_code == chart.get("variable_code"),
            )
            .order_by(ResearchObservation.period_start)
        )
        points = [
            {"period": _date(period), "value": value, "unit": unit}
            for period, value, unit in (await session.execute(stmt)).all()
        ]
        return {**chart, "entity_code": entity_code, "points": points}
    if chart.get("kind") == "indicator":
        stmt = (
            select(Observation.period_start, Observation.value, Observation.unit)
            .join(Country, Country.id == Observation.country_id)
            .join(Indicator, Indicator.id == Observation.indicator_id)
            .where(Country.iso3 == entity_code, Indicator.code == chart.get("indicator_code"))
            .order_by(Observation.period_start)
        )
        points = [
            {"period": _date(period), "value": value, "unit": unit}
            for period, value, unit in (await session.execute(stmt)).all()
        ]
        return {**chart, "entity_code": entity_code, "points": points}
    return chart


async def question_summary(
    session: AsyncSession,
    registry_version: str | None = None,
) -> dict[str, Any]:
    target_version = registry_version or VALIDATION_REGISTRY_VERSION
    rows = (
        await session.execute(
            select(ValidationQuestion).where(
                ValidationQuestion.registry_version == target_version
            )
        )
    ).scalars().all()
    if not rows:
        rows = (await session.execute(select(ValidationQuestion))).scalars().all()
    all_versions = sorted(
        r[0]
        for r in (
            await session.execute(
                select(func.distinct(ValidationQuestion.registry_version))
            )
        ).all()
        if r[0]
    )
    implementation = Counter(r.implementation_status for r in rows)
    validation = Counter(r.research_validation_status for r in rows)
    categories = Counter(r.category for r in rows)
    missing_sources = Counter(
        d.get("source_key", "unknown")
        for r in rows for d in r.missing_datasets
    )
    available_sources = Counter(
        d.get("source_key", "unknown")
        for r in rows for d in r.available_datasets
    )
    return {
        "count": len(rows),
        "registry_version": rows[0].registry_version if rows else target_version,
        "preserved_registry_versions": all_versions,
        "methodology_status": "experimental",
        "by_category": dict(sorted(categories.items())),
        "by_implementation_status": dict(sorted(implementation.items())),
        "by_research_validation_status": dict(sorted(validation.items())),
        "available_dataset_mentions": dict(sorted(available_sources.items())),
        "missing_dataset_mentions": dict(sorted(missing_sources.items())),
        "legacy_assessment": {
            "implemented": 5,
            "partially_addressed": 23,
            "missing": 22,
            "note": "Aggregate only; the prior per-question status mapping is not present in the repository.",
        },
    }
