"""Read-only research API — Mission 2 §17.

Every response carries methodology_status="experimental" where the result
is a research calculation. No endpoint here mutates production config;
there is no promotion endpoint.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.config import get_settings
from app.cycle.execution_modes import parse_execution_spec
from app.cycle.force_definitions import FORCE_DEFINITIONS
from app.cycle.normalization_definitions import ScoringPeriod
from app.research.composite import COMPOSITE_MODELS
from app.research.cycle import CycleModelConfig
from app.research.methodology_registry import (
    METHODOLOGY_REGISTRY,
    MethodologyState,
    methods_for_force,
)
from app.research import service as research_service
from app.research.geography import geography_profile
from app.services import country_service

router = APIRouter(prefix=f"{get_settings().api_prefix}/research", tags=["research"])


def _latest_completed_scoring_period() -> ScoringPeriod:
    today = date.today()
    quarter = (today.month - 1) // 3
    if quarter == 0:
        return ScoringPeriod(today.year - 1, 4)
    return ScoringPeriod(today.year, quarter - 1)


class MethodInfo(BaseModel):
    method_id: str
    force_code: str
    formula_id: str
    version: str
    state: str
    dimension: str
    inputs: list[str]
    interpretation: str
    reference_universe: Optional[str] = None
    units: str
    parameters: dict
    coverage_ceiling: Optional[str] = None
    approval_decision: Optional[str] = None
    limitations: list[str]


class CompositeModelInfo(BaseModel):
    model_id: str
    version: str
    kind: str
    eligible_forces: list[str]
    missing_policy: str
    min_coverage: float
    methodology_status: str = "experimental"
    notes: str


def _method_info(m) -> MethodInfo:
    return MethodInfo(
        method_id=m.method_id, force_code=m.force_code,
        formula_id=m.formula_id, version=m.version,
        state=m.state.value, dimension=m.dimension,
        inputs=list(m.inputs), interpretation=m.interpretation,
        reference_universe=m.reference_universe, units=m.units,
        parameters=dict(m.parameters),
        coverage_ceiling=m.coverage_ceiling,
        approval_decision=m.approval_decision,
        limitations=list(m.limitations),
    )


@router.get("/methods", response_model=list[MethodInfo])
async def list_methods(state: Optional[str] = Query(None)):
    methods = list(METHODOLOGY_REGISTRY.values())
    if state:
        try:
            wanted = MethodologyState(state)
        except ValueError:
            raise HTTPException(422, f"unknown state {state!r}")
        methods = [m for m in methods if m.state is wanted]
    return [_method_info(m) for m in methods]


@router.get("/forces/{force_code}/methods", response_model=list[MethodInfo])
async def force_methods(force_code: str):
    methods = methods_for_force(force_code)
    if not methods:
        raise HTTPException(404, f"no methods for force {force_code!r}")
    return [_method_info(m) for m in methods]


@router.get("/models", response_model=list[CompositeModelInfo])
async def list_models():
    return [
        CompositeModelInfo(
            model_id=m.model_id, version=m.version, kind=m.kind,
            eligible_forces=sorted(m.eligible_forces),
            missing_policy=m.missing_policy, min_coverage=m.min_coverage,
            notes=m.notes,
        )
        for m in COMPOSITE_MODELS.values()
    ]


@router.get("/countries/{iso3}/cycle")
async def country_cycle(
    iso3: str,
    model: str = Query("model_b_domain"),
    execution_mode: Optional[str] = Query(
        None,
        description=(
            "Information-selection mode: retrospective_latest_vintage "
            "(default), strict_as_of or research_assumption. "
            "Strict/assumption require info_cutoff."
        ),
    ),
    info_cutoff: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    country = await country_service.get_country(session, iso3)
    if country is None:
        raise HTTPException(404, f"Country {iso3!r} not found")
    if model not in COMPOSITE_MODELS:
        raise HTTPException(422, f"unknown model {model!r}")
    try:
        execution = parse_execution_spec(execution_mode, info_cutoff)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    period = _latest_completed_scoring_period()
    result = await research_service.composite_at(
        session, country.iso3, period, model, execution=execution
    )
    return {
        "methodology_status": "experimental",
        "execution_mode": result.execution_mode,
        "info_cutoff": (
            execution.info_cutoff.isoformat()
            if execution.info_cutoff else None
        ),
        "composite": {
            "model_id": result.model_id,
            "model_version": result.model_version,
            "score": result.score,
            "included_forces": list(result.included_forces),
            "missing_forces": list(result.missing_forces),
            "excluded_forces": list(result.excluded_forces),
            "weights": result.weights,
            "coverage_ratio": result.coverage_ratio,
            "warnings": list(result.warnings),
            "limitations": list(result.limitations),
        },
        "period": result.scoring_period,
        "backtest_safe": result.backtest_safe,
    }


@router.get("/countries/{iso3}/cycle/history")
async def country_cycle_history(
    iso3: str,
    model: str = Query("model_b_domain"),
    start_year: int = Query(2000, ge=1990, le=2200),
    end_year: Optional[int] = Query(None, ge=1990, le=2200),
    execution_mode: Optional[str] = Query(
        None,
        description=(
            "Information-selection mode: retrospective_latest_vintage "
            "(default), strict_as_of or research_assumption. "
            "Strict/assumption require info_cutoff."
        ),
    ),
    info_cutoff: Optional[date] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    country = await country_service.get_country(session, iso3)
    if country is None:
        raise HTTPException(404, f"Country {iso3!r} not found")
    if model not in COMPOSITE_MODELS:
        raise HTTPException(422, f"unknown model {model!r}")
    try:
        execution = parse_execution_spec(execution_mode, info_cutoff)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc))
    latest = _latest_completed_scoring_period()
    end_year = end_year or latest.year
    if end_year < start_year:
        raise HTTPException(422, "end_year < start_year")
    if (end_year - start_year) > 40:
        raise HTTPException(422, "range too large (max 40 years)")
    result = await research_service.cycle_history(
        session, country.iso3, model, start_year, end_year, latest,
        execution=execution,
    )
    return {
        "methodology_status": "experimental",
        "retrospective": True,
        "execution_mode": result.execution_mode,
        "info_cutoff": (
            execution.info_cutoff.isoformat()
            if execution.info_cutoff else None
        ),
        "model": model,
        "engine_version": result.model_version,
        "country_iso3": result.country_iso3,
        "coverage_ratio": result.coverage_ratio,
        "points": [
            {
                "period": p.period,
                "score": p.score,
                "momentum": p.momentum,
                "stage": p.stage.value if p.stage else None,
                "phase": p.phase.value if p.phase else None,
                "reason": p.reason,
            }
            for p in result.points
        ],
        "transitions": list(result.transitions),
        "warnings": list(result.warnings),
        "backtest_safe": result.backtest_safe,
    }


@router.get("/countries/{iso3}/geography")
async def country_geography(iso3: str):
    profile = geography_profile(iso3.upper())
    if profile is None:
        raise HTTPException(404, f"no geography profile for {iso3!r}")
    return profile


# Mutually-exclusive primary implementation classes (Mission 3 §3).
# Every canonical force is assigned exactly one; counts MUST sum to 17.
PRIMARY_CLASSES = (
    "level_published",   # approved level method publishes a force level
    "dimension_only",    # approved non-level dimensions publish; no level
    "context_profile",   # functional context data; no published dimensions
    "deferred",          # research module registered; nothing functional yet
)


def _primary_classification(fd, methods, approved) -> str:
    if any(m.dimension == "level" for m in approved):
        return "level_published"
    if approved:
        return "dimension_only"
    if fd.live_indicator_codes or (
        fd.code == "geography" and methods
    ):
        return "context_profile"
    return "deferred"


@router.get("/progress")
async def research_progress(session: AsyncSession = Depends(get_session)):
    """Authoritative per-force implementation status (§22 + Mission 3 §3).

    `primary_classification` is mutually exclusive and its counts always sum
    to 17. Secondary attributes (approval_state, published_dimensions,
    has_context_profile) may overlap across forces and are labelled as
    independent attributes."""
    latest = _latest_completed_scoring_period()
    forces = []
    counts: dict[str, int] = {c: 0 for c in PRIMARY_CLASSES}
    for fd in FORCE_DEFINITIONS:
        methods = methods_for_force(fd.code)
        approved = [m for m in methods
                    if m.state is MethodologyState.approved_production]
        primary = _primary_classification(fd, methods, approved)
        counts[primary] += 1
        has_level = primary == "level_published"
        approval_state = (
            "partial" if (has_level and fd.coverage_ceiling
                          and fd.coverage_ceiling.value == "partial")
            else "approved" if has_level else "none"
        )
        forces.append({
            "force_code": fd.code,
            "force_name": fd.name,
            # primary implementation type — mutually exclusive
            "primary_classification": primary,
            # independent attributes (may overlap)
            "approval_state": approval_state,
            "published_dimensions": sorted({m.dimension for m in approved}),
            "has_context_profile": primary == "context_profile"
                or any(m.state is MethodologyState.context_only
                       for m in methods),
            "experimental_methods": [
                m.method_id for m in methods
                if m.state is MethodologyState.experimental
            ],
            "methods": [m.method_id for m in methods],
            "coverage_ceiling": (fd.coverage_ceiling.value
                                 if fd.coverage_ceiling else None),
            "live_inputs": list(fd.live_indicator_codes),
        })
    return {
        "as_of_period": f"{latest.year}-Q{latest.quarter}",
        "total_forces": len(FORCE_DEFINITIONS),
        "counts": counts,
        "counts_sum_to_total": sum(counts.values()) == len(FORCE_DEFINITIONS),
        "forces": forces,
    }
