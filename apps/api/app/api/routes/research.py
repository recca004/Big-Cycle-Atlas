"""Read-only research API — Mission 2 §17.

Every response carries methodology_status="experimental" where the result
is a research calculation. No endpoint here mutates production config;
there is no promotion endpoint.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.core.config import get_settings
from app.cycle.execution_modes import parse_execution_spec
from app.cycle.force_definitions import FORCE_DEFINITIONS
from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    ScoringPeriod,
)
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


_POSITIONS_CACHE: dict = {}
_POSITIONS_TTL = 3600  # seconds — positions only change on new data


@router.get("/cycle/positions")
async def cycle_positions(
    model: str = Query("model_b_domain"),
    session: AsyncSession = Depends(get_session),
):
    """Latest classified cycle position for every tracked country.

    One request so the Observatory clock doesn't fan out N slow
    per-country history calls. Each country runs on its own DB session
    concurrently; a country that fails classifies as unclassified
    rather than failing the whole response."""
    import asyncio

    from sqlalchemy import select

    from app.db.session import get_sessionmaker
    from app.models import Country

    if model not in COMPOSITE_MODELS:
        raise HTTPException(422, f"unknown model {model!r}")
    import time

    cached = _POSITIONS_CACHE.get(model)
    if cached and time.monotonic() - cached[0] < _POSITIONS_TTL:
        return cached[1]
    countries = (
        (await session.execute(select(Country).order_by(Country.name)))
        .scalars()
        .all()
    )
    latest = _latest_completed_scoring_period()
    sm = get_sessionmaker()

    async def _one(iso3: str, name: str) -> dict:
        base = {
            "iso3": iso3,
            "name": name,
            "stage": None,
            "phase": None,
            "score": None,
            "momentum": None,
            "period": None,
            "classified": False,
        }
        try:
            async with sm() as s:
                result = await research_service.cycle_history(
                    s, iso3, model, 2000, latest.year, latest
                )
            if not result.points:
                return base
            last = result.points[-1]
            return {
                **base,
                "stage": last.stage.value if last.stage else None,
                "phase": last.phase.value if last.phase else None,
                "score": last.score,
                "momentum": last.momentum,
                "period": last.period,
                "classified": last.stage is not None,
            }
        except Exception:
            return base

    rows = await asyncio.gather(
        *[_one(c.iso3, c.name) for c in countries]
    )
    payload = {
        "methodology_status": "experimental",
        "retrospective": True,
        "model": model,
        "model_version": COMPOSITE_MODELS[model].version,
        "scoring_period": f"{latest.year}-Q{latest.quarter}",
        "positions": list(rows),
    }
    _POSITIONS_CACHE[model] = (time.monotonic(), payload)
    return payload


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
        # §24 reproducible run manifest — exact model/config/data identities
        "run_manifest": {
            "composite_model_id": model,
            "composite_model_version": (
                COMPOSITE_MODELS[model].version
            ),
            "classifier_id": result.model_id,
            "classifier_version": result.model_version,
            "normalization_version": (
                CURRENT_MODEL_VERSION.version_id
            ),
            "execution_mode": result.execution_mode,
            "info_cutoff": (
                execution.info_cutoff.isoformat()
                if execution.info_cutoff else None
            ),
            "evaluation_period": [
                f"{start_year}-Q4", f"{end_year}-Q4",
            ],
            "as_of_latest_period": f"{latest.year}-Q{latest.quarter}",
            "input_vintages": (
                "latest stored" if not execution.is_strict
                else "release-date eligible"
            ),
            "deterministic_rerun": (
                "same code version + same stored vintages + same spec "
                "reproduce this response"
            ),
        },
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


@router.get("/execution-modes")
async def list_execution_modes():
    """Supported historical information-selection modes (Mission 4 §23)."""
    from app.cycle.execution_modes import ExecutionMode

    return {
        "modes": [
            {
                "mode": ExecutionMode.CURRENT_LATEST.value,
                "description": (
                    "Latest-vintage, period-complete selection — the standard "
                    "production path; NOT a backtest."
                ),
                "requires_info_cutoff": False,
                "backtest_safe_by_construction": False,
            },
            {
                "mode": ExecutionMode.RETROSPECTIVE_LATEST_VINTAGE.value,
                "description": (
                    "Same selection used for looking back. Explicitly not a "
                    "strict as-of reconstruction — later revisions are visible."
                ),
                "requires_info_cutoff": False,
                "backtest_safe_by_construction": False,
            },
            {
                "mode": ExecutionMode.STRICT_AS_OF.value,
                "description": (
                    "Only observations with positive evidence the value "
                    "existed at/before the info cutoff are eligible: "
                    "provider release_date OR Atlas first-observed "
                    "retrieved_at (conservative — retrieval only delays "
                    "eligibility). Rows without evidence are excluded, "
                    "never silently included. No fallback to latest-vintage."
                ),
                "requires_info_cutoff": True,
                "backtest_safe_by_construction": False,
            },
            {
                "mode": ExecutionMode.RESEARCH_ASSUMPTION.value,
                "description": (
                    "Eligibility estimated via documented provider release "
                    "lags (release_calendar.py) — research assumptions, not "
                    "verified publication dates."
                ),
                "requires_info_cutoff": True,
                "backtest_safe_by_construction": False,
            },
        ],
        "backtest_safe_rule": (
            "backtest_safe=True only when ALL required inputs, reference "
            "data and model availability conditions satisfy strict rules — "
            "the mode alone never confers safety."
        ),
        "evidence_types": {
            "provider_release_date": {
                "description": (
                    "Publication date supplied by the provider — the only "
                    "evidence that proves when a value first became public."
                ),
                "eligible_modes": ["strict_as_of"],
            },
            "atlas_first_observed": {
                "description": (
                    "retrieved_at on the stored vintage — proves Atlas had "
                    "this exact value by that timestamp. Conservative "
                    "strict evidence; does NOT establish provider "
                    "publication date."
                ),
                "eligible_modes": ["strict_as_of"],
            },
            "assumed_release_lag": {
                "description": (
                    "Documented provider lag estimates — research "
                    "assumptions only, never evidence."
                ),
                "eligible_modes": ["research_assumption"],
            },
        },
    }


@router.get("/release-evidence")
async def provider_release_evidence():
    """Provider-level release-date coverage matrix (Mission 4 §21).

    Reports what publication-date evidence actually exists in the Atlas —
    unknowns are recorded, never invented."""
    from app.research.release_calendar import PROVIDER_RELEASE_METADATA

    return {
        "providers": [
            {
                "source_key": m.source_key,
                "provider": m.provider,
                "has_release_dates": m.has_release_dates,
                "has_revision_dates": m.has_revision_dates,
                "has_vintage_history": m.has_vintage_history,
                "publication_calendar": m.publication_calendar,
                "historical_archive": m.historical_archive,
                "assumed_lag_days": m.assumed_lag_days,
                "notes": m.notes,
            }
            for m in PROVIDER_RELEASE_METADATA.values()
        ],
        "disclaimer": (
            "assumed_lag_days values are RESEARCH ASSUMPTIONS for the "
            "research_assumption execution mode — not verified publication "
            "dates."
        ),
    }


@router.get("/countries/{iso3}/availability")
async def country_data_availability(
    iso3: str,
    session: AsyncSession = Depends(get_session),
):
    """Historical data availability for a country (Mission 4 §29).

    Per indicator: observation/vintage counts, period range, and how many
    rows carry provider release evidence — the actual prerequisite for
    strict as-of evaluation."""
    from sqlalchemy import func, select

    from app.models import DataSource, Indicator, Observation

    country = await country_service.get_country(session, iso3)
    if country is None:
        raise HTTPException(404, f"Country {iso3!r} not found")

    rows = (
        await session.execute(
            select(
                Indicator.code,
                DataSource.key,
                func.count(Observation.id),
                func.min(Observation.period_start),
                func.max(Observation.period_start),
                func.count(Observation.release_date),
                func.count(Observation.retrieved_at),
                func.min(Observation.retrieved_at),
                func.max(Observation.vintage_number),
            )
            .join(Observation, Observation.indicator_id == Indicator.id)
            .join(DataSource, DataSource.id == Observation.data_source_id)
            .where(Observation.country_id == country.id)
            .group_by(Indicator.code, DataSource.key)
            .order_by(Indicator.code)
        )
    ).all()
    return {
        "country": country.iso3,
        "indicators": [
            {
                "indicator_code": code,
                "source_key": source,
                "observation_count": n,
                "earliest_period": (
                    earliest.date().isoformat() if earliest else None
                ),
                "latest_period": (
                    latest.date().isoformat() if latest else None
                ),
                "with_release_evidence": with_release,
                "with_retrieval_evidence": with_retrieved,
                "first_observed_at": (
                    first_seen.isoformat() if first_seen else None
                ),
                "max_vintage": max_vintage,
                # Both evidence types qualify a row for strict_as_of;
                # retrieval evidence only ever delays eligibility.
                "strict_eligible": (with_release + with_retrieved) > 0,
            }
            for code, source, n, earliest, latest, with_release,
            with_retrieved, first_seen, max_vintage in rows
        ],
        "note": (
            "strict_eligible reflects positive evidence a value existed — "
            "provider release_date OR Atlas first-observed retrieved_at. "
            "Retrieval evidence is conservative: it can only delay "
            "eligibility vs the true publication date, never accelerate it."
        ),
    }


@router.get("/reference-availability")
async def reference_availability(session: AsyncSession = Depends(get_session)):
    """Reference-population availability per universe (Mission 4 §29)."""
    from sqlalchemy import func, select

    from app.models.reference_observation import ReferenceObservation

    rows = (
        await session.execute(
            select(
                ReferenceObservation.universe_code,
                ReferenceObservation.indicator_code,
                func.count(ReferenceObservation.id),
                func.min(ReferenceObservation.period_start),
                func.max(ReferenceObservation.period_start),
                func.count(func.distinct(ReferenceObservation.country_iso3)),
            )
            .group_by(
                ReferenceObservation.universe_code,
                ReferenceObservation.indicator_code,
            )
            .order_by(ReferenceObservation.universe_code)
        )
    ).all()
    return {
        "universes": [
            {
                "universe_code": u,
                "indicator_code": ind,
                "row_count": n,
                "earliest_period": (
                    earliest.date().isoformat() if earliest else None
                ),
                "latest_period": (
                    latest.date().isoformat() if latest else None
                ),
                "country_count": cc,
                "has_release_evidence": False,
            }
            for u, ind, n, earliest, latest, cc in rows
        ],
        "note": (
            "Reference observations carry no provider release evidence — "
            "strict as-of mode cannot use them (§22), which is reported, "
            "not worked around."
        ),
    }


@router.get("/diagnostics")
async def model_diagnostics():
    """Stored retrospective model-diagnostics manifest (Mission 4 §26/§29).

    Serves the committed .dev/MODEL_DIAGNOSTICS.json produced by
    scripts/generate_model_diagnostics.py — a reproducible run manifest,
    never a live recalculation."""
    import json
    from pathlib import Path

    manifest_path = (
        Path(__file__).resolve().parents[5] / ".dev" / "MODEL_DIAGNOSTICS.json"
    )
    if not manifest_path.exists():
        raise HTTPException(
            404,
            "diagnostics manifest not generated — run "
            "scripts/generate_model_diagnostics.py",
        )
    return json.loads(manifest_path.read_text(encoding="utf-8"))


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


# --- Forecast research (Mission 5 §10-§13) -------------------------------------

_DIAGNOSTICS_PATH = (
    Path(__file__).resolve().parents[5] / ".dev" / "MODEL_DIAGNOSTICS.json"
)


def _load_transition_dataset():
    """Build the transition dataset from the retrospective diagnostics
    manifest. Returns (transitions, scored_periods, generated_at) or None."""
    import json

    from app.research.forecast import TransitionRecord

    if not _DIAGNOSTICS_PATH.exists():
        return None
    manifest = json.loads(_DIAGNOSTICS_PATH.read_text(encoding="utf-8"))
    transitions: list[TransitionRecord] = []
    scored_periods: set[str] = set()
    for model_id, model in manifest["models"].items():
        for iso3, c in model["countries"].items():
            scored_periods.update(
                p["period"] for p in c["points"] if p["score"] is not None
            )
            for t in c.get("transitions_detail", []):
                if t.get("reason") == "initial" or "from" not in t:
                    continue
                transitions.append(TransitionRecord(
                    country_iso3=iso3, period=t["period"],
                    from_stage=t["from"], to_stage=t["to"],
                    model_id=model_id,
                ))
    return transitions, sorted(scored_periods), manifest["generated_at"]


async def _strict_eligible_periods(session: AsyncSession) -> int:
    """Live count: observation rows with ANY strict evidence
    (provider release_date or Atlas retrieved_at) — both non-null by
    construction for retrieved_at, so this counts rows eligible under
    at least one evidence type."""
    from sqlalchemy import func, select

    from app.models import Observation

    return int((await session.execute(
        select(func.count(Observation.id)).where(Observation.retrieved_at.isnot(None))
    )).scalar() or 0)


def _readiness_json(report) -> dict:
    return {
        "model_id": report.model_id,
        "model_version": report.model_version,
        "requirements_version": report.requirements_version,
        "overall_available": report.overall_available,
        "blockers": list(report.blockers),
        "total_scored_periods": report.total_scored_periods,
        "total_genuine_transitions": report.total_genuine_transitions,
        "strict_eligible_periods": report.strict_eligible_periods,
        "horizons": [
            {
                "horizon": hr.horizon.value,
                "horizon_quarters": hr.horizon_quarters,
                "available": hr.available,
                "unavailable_reason": hr.unavailable_reason,
                "eligible_samples": hr.eligible_samples,
                "positive_transitions": hr.positive_transitions,
                "gates": [
                    {
                        "gate": g.gate,
                        "passed": g.passed,
                        "value": g.value,
                        "requirement": g.requirement,
                        "note": g.note or None,
                    }
                    for g in hr.gates
                ],
            }
            for hr in report.horizon_results
        ],
    }


@router.get("/forecast/readiness")
async def forecast_readiness(session: AsyncSession = Depends(get_session)):
    """Explicit readiness evaluation per model and horizon (§11).

    Transition data comes from the retrospective diagnostics manifest
    (labeled with its generated_at — latest-vintage, NOT strict);
    strict-eligible sample counts are computed live. A failed gate
    means that horizon stays unavailable — no probability is emitted."""
    from app.research.forecast import evaluate_readiness

    dataset = _load_transition_dataset()
    if dataset is None:
        raise HTTPException(
            503,
            "MODEL_DIAGNOSTICS.json missing — run "
            "scripts/generate_model_diagnostics.py first",
        )
    transitions, scored_periods, generated_at = dataset
    strict_periods = await _strict_eligible_periods(session)

    models = {}
    for model_id, model in COMPOSITE_MODELS.items():
        model_transitions = [
            t for t in transitions if t.model_id == model_id
        ]
        report = evaluate_readiness(
            model_id, model.version, scored_periods,
            model_transitions, strict_periods,
        )
        models[model_id] = _readiness_json(report)

    return {
        "methodology_status": "experimental",
        "dataset": {
            "source": ".dev/MODEL_DIAGNOSTICS.json",
            "generated_at": generated_at,
            "execution_mode": "retrospective_latest_vintage",
            "warning": (
                "latest-vintage transitions — NOT release-date-safe; "
                "usable for readiness evaluation, not backtesting"
            ),
        },
        "models": models,
        "any_available": any(
            m["overall_available"] for m in models.values()
        ),
    }


@router.get("/forecast/{iso3}")
async def country_forecast(
    iso3: str,
    model: str = Query("model_a_equal"),
    horizon: str = Query("1y"),
    session: AsyncSession = Depends(get_session),
):
    """Stage-transition forecast contract (§10). Today every horizon is
    gated: the response returns availability + reasons, NEVER a
    probability. When gates pass in future, stage_probabilities,
    calibration and run_manifest fields appear."""
    from app.research.forecast import ForecastHorizon, evaluate_readiness

    if model not in COMPOSITE_MODELS:
        raise HTTPException(404, f"Unknown model {model!r}")
    try:
        hz = ForecastHorizon(horizon)
    except ValueError:
        raise HTTPException(422, f"Unknown horizon {horizon!r}") from None

    country = await country_service.get_country(session, iso3)
    if country is None:
        raise HTTPException(404, f"Country {iso3!r} not found")

    dataset = _load_transition_dataset()
    strict_periods = await _strict_eligible_periods(session)
    transitions, scored_periods, generated_at = (
        dataset if dataset else ([], [], None)
    )
    report = evaluate_readiness(
        model, COMPOSITE_MODELS[model].version, scored_periods,
        [t for t in transitions if t.model_id == model], strict_periods,
    )
    hr = next(h for h in report.horizon_results if h.horizon is hz)
    return {
        "methodology_status": "experimental",
        "country": country.iso3,
        "model_id": model,
        "model_version": COMPOSITE_MODELS[model].version,
        "horizon": hz.value,
        "forecast": {
            "available": hr.available,
            "unavailable_reason": hr.unavailable_reason,
            # Probability fields intentionally absent while unavailable —
            # a gate failure never emits a fictional probability.
            "stage_probabilities": None,
            "calibration": None,
        },
        "evidence": {
            "eligible_samples": hr.eligible_samples,
            "positive_transitions": hr.positive_transitions,
            "dataset_generated_at": generated_at,
        },
    }
