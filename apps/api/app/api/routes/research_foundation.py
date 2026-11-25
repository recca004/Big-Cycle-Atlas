"""Scientific-foundation read API."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.models import (
    CrisisCoverage, CrisisEvent, DatasetRightsRegistry,
    EvaluationResult, EvidenceStatusEntry, HypothesisProtocol,
    PredictionLedgerEntry, ResearchObservation,
    ResearchPopulationMembership, TheoryRegistryEntry,
)
from app.research.h01 import evaluate_h01
from app.research.scientific_registry import TIMESCALES

router = APIRouter(prefix=f"{get_settings().api_prefix}/research/foundation", tags=["research-foundation"])


def _date(value):
    return value.isoformat() if value else None


@router.get("/theory-registry")
async def theory_registry(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(TheoryRegistryEntry).order_by(TheoryRegistryEntry.theory_code))).scalars().all()
    return {
        "methodology_status": "experimental", "count": len(rows),
        "entries": [
            {
                "theory_code": r.theory_code, "version": r.version,
                "source": {"title": r.source_title, "author": r.source_author, "edition": r.source_edition, "section": r.chapter_section, "publication_date": _date(r.publication_date)},
                "concept": r.concept, "atlas_interpretation": r.atlas_interpretation,
                "framework_differences": r.framework_differences,
                "measurement_limitations": r.measurement_limitations,
                "framework_scope": r.framework_scope,
                "atlas_operational": r.atlas_operational,
                "testable_status": r.testable_status,
                "registered_at": _date(r.registered_at),
                "content_checksum": r.content_checksum,
            } for r in rows
        ],
    }


@router.get("/timescales")
async def research_timescales():
    return {
        "methodology_status": "candidate_definitions_not_natural_laws",
        "timescales": TIMESCALES,
        "note": "The production national-condition models remain short/medium experimental research models; no long-clock stage position is asserted.",
    }


@router.get("/hypotheses")
async def hypotheses(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(HypothesisProtocol).order_by(HypothesisProtocol.hypothesis_code, HypothesisProtocol.protocol_version))).scalars().all()
    return {
        "methodology_status": "registered_protocols", "count": len(rows),
        "protocols": [{c.name: getattr(r, c.name) for c in r.__table__.columns if c.name != "id"} for r in rows],
    }


@router.get("/populations")
async def research_populations(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(ResearchPopulationMembership).order_by(ResearchPopulationMembership.population_code, ResearchPopulationMembership.entity_code))).scalars().all()
    return {"count": len(rows), "memberships": [{c.name: getattr(r, c.name) for c in r.__table__.columns if c.name != "id"} for r in rows]}


@router.get("/research-observations/summary")
async def research_observation_summary(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(
        ResearchObservation.source_key, ResearchObservation.dataset_version,
        ResearchObservation.entity_code,
        func.count(ResearchObservation.id),
        func.min(ResearchObservation.period_start),
        func.max(ResearchObservation.period_start),
        func.count(func.distinct(ResearchObservation.variable_code)),
        func.count(ResearchObservation.release_date),
        func.count(ResearchObservation.vintage_date),
    ).group_by(
        ResearchObservation.source_key, ResearchObservation.dataset_version,
        ResearchObservation.entity_code,
    ).order_by(ResearchObservation.source_key, ResearchObservation.entity_code))).all()
    return {"count": len(rows), "rows": [
        {"source_key": r[0], "dataset_version": r[1], "entity_code": r[2],
         "observations": r[3], "earliest_period": _date(r[4]), "latest_period": _date(r[5]),
         "variables": r[6], "release_dates": r[7], "vintage_dates": r[8]}
        for r in rows
    ]}


@router.get("/crisis-events")
async def crisis_events(
    event_type: Optional[str] = Query(None),
    entity: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(CrisisEvent).order_by(CrisisEvent.entity_code, CrisisEvent.start_period)
    if event_type:
        stmt = stmt.where(CrisisEvent.event_type == event_type)
    if entity:
        stmt = stmt.where(CrisisEvent.entity_code == entity.upper())
    if source:
        stmt = stmt.where(CrisisEvent.source_key == source)
    rows = (await session.execute(stmt)).scalars().all()
    return {"count": len(rows), "events": [
        {"id": r.id, "source_key": r.source_key, "dataset_version": r.dataset_version,
         "entity_code": r.entity_code, "entity_name": r.entity_name,
         "event_type": r.event_type, "event_state": r.event_state,
         "classification": r.classification,
         "start_period": _date(r.start_period), "end_period": _date(r.end_period),
         "dating_precision": r.dating_precision,
         "source_definition": r.source_definition,
         "source_reference": r.source_reference, "revision_number": r.revision_number}
        for r in rows
    ]}


@router.get("/crisis-coverage")
async def crisis_coverage(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(
        CrisisCoverage.source_key, CrisisCoverage.dataset_version,
        CrisisCoverage.entity_code, CrisisCoverage.event_type,
        func.count(CrisisCoverage.id), func.min(CrisisCoverage.period_start),
        func.max(CrisisCoverage.period_start),
    ).group_by(
        CrisisCoverage.source_key, CrisisCoverage.dataset_version,
        CrisisCoverage.entity_code, CrisisCoverage.event_type,
    ))).all()
    return {"count": len(rows), "coverage": [
        {"source_key": r[0], "dataset_version": r[1], "entity_code": r[2],
         "event_type": r[3], "periods": r[4], "earliest_period": _date(r[5]),
         "latest_period": _date(r[6])} for r in rows
    ]}


@router.get("/predictions")
async def prediction_ledger(
    hypothesis: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(PredictionLedgerEntry).order_by(PredictionLedgerEntry.recorded_at.desc()).limit(limit)
    if hypothesis:
        stmt = stmt.where(PredictionLedgerEntry.hypothesis_code == hypothesis.upper())
    rows = (await session.execute(stmt)).scalars().all()
    return {"count": len(rows), "predictions": [
        {c.name: getattr(r, c.name) for c in r.__table__.columns if c.name != "id"}
        for r in rows
    ]}


@router.get("/evaluations")
async def evaluations(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(EvaluationResult).order_by(EvaluationResult.started_at.desc()))).scalars().all()
    return {"count": len(rows), "evaluations": [{c.name: getattr(r, c.name) for c in r.__table__.columns if c.name != "id"} for r in rows]}


@router.get("/h01")
async def h01_live(session: AsyncSession = Depends(get_session)):
    return await evaluate_h01(session)


@router.get("/dataset-rights")
async def dataset_rights(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(DatasetRightsRegistry))).scalars().all()
    return {"count": len(rows), "rights": [{c.name: getattr(r, c.name) for c in r.__table__.columns if c.name != "id"} for r in rows]}


@router.get("/evidence-status")
async def evidence_status(session: AsyncSession = Depends(get_session)):
    rows = (await session.execute(select(EvidenceStatusEntry).order_by(EvidenceStatusEntry.subject_type, EvidenceStatusEntry.subject_key))).scalars().all()
    return {"count": len(rows), "entries": [{c.name: getattr(r, c.name) for c in r.__table__.columns if c.name != "id"} for r in rows]}
