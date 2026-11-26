from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import Country, DataSource, Indicator, Observation, ReferenceObservation, SourceSeries
from app.research.power_registry import POWER_MEASURES_BY_INDICATOR
from app.research import observatory as observatory_service
from app.research.composite import COMPOSITE_MODELS
from app.research.model_diagnostics import compare_core_histories

router = APIRouter(prefix="/api/observatory", tags=["observatory"])


class RefreshRequest(BaseModel):
    model: str = "model_b_domain"
    collect_providers: bool = False
    sources: Optional[list[str]] = None


async def _strict_count(session: AsyncSession) -> int:
    """Fully release-date-safe scored periods available to forecast gates.

    Retrieved observation rows are prospective provenance, not strict
    historical evidence. Until a strict-as-of composite run exists, zero
    scored periods qualify.
    """
    return 0


@router.get("/overview")
async def observatory_overview(
    model: str = Query("model_b_domain"),
    incumbent: str = Query("USA"),
    challenger: str = Query("CHN"),
    start_year: int = Query(1980, ge=1960, le=2200),
    session: AsyncSession = Depends(get_session),
):
    if model not in COMPOSITE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown model {model!r}")
    core = await observatory_service.compute_core_observatory(
        session, model_id=model, start_year=start_year
    )
    strict_cnt = await _strict_count(session)
    transition = observatory_service.build_transition_monitor(
        core,
        incumbent_iso3=incumbent,
        challenger_iso3=challenger,
        strict_eligible_periods=strict_cnt,
    )
    freshness, daily_changes = (
        await observatory_service.build_freshness_and_changes(session, core)
    )
    return {
        "methodology_status": core["methodology_status"],
        "normalization_version": core["normalization_version"],
        "model": core["model"],
        "scoring_period": core["scoring_period"],
        "available_periods": core["available_periods"],
        "countries": core["countries"],
        "currency_evidence": core.get("currency_evidence"),
        "power_summary": core["power_summary"],
        "transition_monitor": transition,
        "freshness": freshness,
        "daily_changes": daily_changes,
        "refresh_job": observatory_service.get_refresh_job_status(),
    }


@router.get("/model-comparison")
async def observatory_model_comparison(
    start_year: int = Query(1980, ge=1960, le=2200),
    period: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    """Actual latest/requested-period stage markers for every experimental model."""
    cores = {
        model_id: await observatory_service.compute_core_observatory(
            session, model_id=model_id, start_year=start_year
        )
        for model_id in COMPOSITE_MODELS
    }
    reference = cores["model_b_domain"]
    active_period = period or (reference["available_periods"][-1] if reference["available_periods"] else None)
    rows = []
    for country in reference["countries"]:
        row = {"iso3": country["iso3"], "name": country["name"], "models": {}}
        for model_id, core in cores.items():
            model_country = next((c for c in core["countries"] if c["iso3"] == country["iso3"]), None)
            point = None
            if model_country:
                point = next(
                    (p for p in model_country["history"] if p["period"] == active_period),
                    model_country["history"][-1] if model_country["history"] else None,
                )
            row["models"][model_id] = {
                "stage": point.get("stage") if point else None,
                "score": point.get("score") if point else None,
                "momentum": point.get("momentum") if point else None,
                "period": point.get("period") if point else None,
                "coverage_ratio": model_country.get("coverage_ratio") if model_country else None,
            }
        rows.append(row)
    model_ids = list(COMPOSITE_MODELS)
    equivalence = {}
    for i, left in enumerate(model_ids):
        for right in model_ids[i + 1:]:
            comparison = compare_core_histories(cores[left], cores[right])
            equivalence[f"{left}__{right}"] = {
                "comparisons": comparison.comparisons,
                "exact_score_share": comparison.exact_score_share,
                "near_score_share": comparison.near_score_share,
                "exact_stage_share": comparison.exact_stage_share,
                "equivalent_under_current_data": comparison.materially_equivalent,
                "distinct_weighting_method": True,
                "distinct_outputs_under_current_data": not comparison.materially_equivalent,
                "shared_input_datasets": True,
                "independent_evidence": False,
            }
    return {
        "cycle_label": "experimental_domestic_condition_cycle",
        "requested_period": period,
        "active_period": active_period,
        "start_year": start_year,
        "models": [
            {
                "model_id": model_id,
                "model_version": spec.version,
                "kind": spec.kind,
                "notes": spec.notes,
            }
            for model_id, spec in COMPOSITE_MODELS.items()
        ],
        "countries": rows,
        "equivalence": equivalence,
        "note": (
            "All four composite models weight shared underlying observations in the same "
            "experimental domestic-condition cycle; none provide statistically independent "
            "empirical evidence. Stage differences measure model specification sensitivity, "
            "and materially equivalent models are not independent confirmation."
        ),
    }


@router.get("/series")
async def observatory_series(
    indicator: str = Query("GDP_CURRENT_USD"),
    start_year: int = Query(1970, ge=1800, le=2200),
    world_share: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    """Latest-vintage measure history across all tracked countries."""
    denominator_by_year: dict[int, float] = {}
    denominator_entity = None
    if world_share:
        definition = POWER_MEASURES_BY_INDICATOR.get(indicator)
        if not definition or not definition.global_denominator_code:
            raise HTTPException(
                status_code=422,
                detail=f"No verified world denominator is registered for {indicator!r}",
            )
        ref_vintage = (
            select(
                ReferenceObservation.period_start.label("period_start"),
                func.max(ReferenceObservation.vintage_number).label("vintage"),
            )
            .where(ReferenceObservation.universe_code == "world_wdi_denominator_v1")
            .where(ReferenceObservation.indicator_code == indicator)
            .where(ReferenceObservation.country_iso3 == "WLD")
            .group_by(ReferenceObservation.period_start)
            .subquery()
        )
        denominator_rows = (
            await session.execute(
                select(ReferenceObservation.period_start, ReferenceObservation.value)
                .select_from(ReferenceObservation)
                .join(
                    ref_vintage,
                    (ReferenceObservation.period_start == ref_vintage.c.period_start)
                    & (ReferenceObservation.vintage_number == ref_vintage.c.vintage),
                )
                .where(ReferenceObservation.universe_code == "world_wdi_denominator_v1")
                .where(ReferenceObservation.indicator_code == indicator)
                .where(ReferenceObservation.country_iso3 == "WLD")
            )
        ).all()
        denominator_by_year = {period.year: value for period, value in denominator_rows}
        denominator_entity = "WLD"
    latest_vintage = (
        select(
            Observation.country_id.label("country_id"),
            Observation.source_series_id.label("source_series_id"),
            Observation.period_start.label("period_start"),
            func.max(Observation.vintage_number).label("vintage"),
        )
        .group_by(
            Observation.country_id,
            Observation.source_series_id,
            Observation.period_start,
        )
        .subquery()
    )
    rows = (
        await session.execute(
            select(
                Country.iso3,
                Indicator.name,
                Indicator.unit,
                Observation.period_start,
                Observation.value,
                Observation.vintage_number,
                DataSource.name.label("source"),
            )
            .select_from(Observation)
            .join(Country, Country.id == Observation.country_id)
            .join(Indicator, Indicator.id == Observation.indicator_id)
            .join(DataSource, DataSource.id == Observation.data_source_id)
            .join(
                latest_vintage,
                (Observation.country_id == latest_vintage.c.country_id)
                & (Observation.source_series_id == latest_vintage.c.source_series_id)
                & (Observation.period_start == latest_vintage.c.period_start)
                & (Observation.vintage_number == latest_vintage.c.vintage),
            )
            .where(Indicator.code == indicator)
            .where(func.extract("year", Observation.period_start) >= start_year)
            .order_by(Country.iso3, Observation.period_start)
        )
    ).all()
    countries: dict[str, dict] = {}
    for iso3, name, unit, period, value, vintage, source in rows:
        display_value = value
        denominator = denominator_by_year.get(period.year) if world_share else None
        if world_share:
            if denominator in (None, 0):
                continue
            display_value = value / denominator * 100
        entry = countries.setdefault(
            iso3,
            {
                "iso3": iso3,
                "indicator_name": f"{name} — global share" if world_share else name,
                "unit": "% of world" if world_share else unit,
                "source": source,
                "denominator_entity": denominator_entity,
                "points": [],
            },
        )
        entry["points"].append(
            {
                "period": period.year,
                "value": display_value,
                "vintage": vintage,
            }
        )
    return {
        "indicator": indicator,
        "start_year": start_year,
        "world_share": world_share,
        "denominator_entity": denominator_entity,
        "countries": list(countries.values()),
    }


@router.get("/coverage")
async def observatory_coverage(
    session: AsyncSession = Depends(get_session),
):
    """Bounded raw-observation coverage for the eight tracked countries."""
    rows = (
        await session.execute(
            select(
                Country.iso3,
                Country.name,
                Indicator.code,
                Indicator.name,
                Indicator.unit,
                Indicator.frequency,
                DataSource.key,
                func.min(Observation.period_start).label("earliest"),
                func.max(Observation.period_start).label("latest"),
                func.count(func.distinct(Observation.period_start)).label(
                    "period_count"
                ),
            )
            .select_from(Observation)
            .join(Country, Country.id == Observation.country_id)
            .join(Indicator, Indicator.id == Observation.indicator_id)
            .join(SourceSeries, SourceSeries.id == Observation.source_series_id)
            .join(DataSource, DataSource.id == Observation.data_source_id)
            .group_by(
                Country.iso3,
                Country.name,
                Indicator.code,
                Indicator.name,
                Indicator.unit,
                Indicator.frequency,
                DataSource.key,
            )
            .order_by(Country.iso3, Indicator.code, DataSource.key)
        )
    ).all()
    return {
        "coverage_kind": "raw_observations_all_vintages",
        "countries": 8,
        "series": [
            {
                "country": iso3,
                "country_name": name,
                "indicator": code,
                "indicator_name": indicator_name,
                "unit": unit,
                "frequency": frequency,
                "source": source,
                "earliest_period": earliest.date().isoformat() if earliest else None,
                "latest_period": latest.date().isoformat() if latest else None,
                "periods": int(period_count),
            }
            for (
                iso3,
                name,
                code,
                indicator_name,
                unit,
                frequency,
                source,
                earliest,
                latest,
                period_count,
            ) in rows
        ],
    }


@router.get("/transition")
async def observatory_transition(
    incumbent: str = Query("USA"),
    challenger: str = Query("CHN"),
    model: str = Query("model_b_domain"),
    start_year: int = Query(1980, ge=1960, le=2200),
    session: AsyncSession = Depends(get_session),
):
    if model not in COMPOSITE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown model {model!r}")
    core = await observatory_service.compute_core_observatory(
        session, model_id=model, start_year=start_year
    )
    strict_cnt = await _strict_count(session)
    return observatory_service.build_transition_monitor(
        core,
        incumbent_iso3=incumbent,
        challenger_iso3=challenger,
        strict_eligible_periods=strict_cnt,
    )


@router.get("/freshness")
async def observatory_freshness(
    model: str = Query("model_b_domain"),
    session: AsyncSession = Depends(get_session),
):
    if model not in COMPOSITE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown model {model!r}")
    core = await observatory_service.compute_core_observatory(
        session, model_id=model
    )
    freshness, _ = await observatory_service.build_freshness_and_changes(
        session, core
    )
    return freshness


@router.get("/changes")
async def observatory_changes(
    model: str = Query("model_b_domain"),
    session: AsyncSession = Depends(get_session),
):
    if model not in COMPOSITE_MODELS:
        raise HTTPException(status_code=422, detail=f"Unknown model {model!r}")
    core = await observatory_service.compute_core_observatory(
        session, model_id=model
    )
    _, daily_changes = await observatory_service.build_freshness_and_changes(
        session, core
    )
    return daily_changes


@router.get("/refresh/status")
async def observatory_refresh_status():
    return observatory_service.get_refresh_job_status()


@router.post("/refresh")
async def observatory_refresh(
    body: RefreshRequest | None = None,
    session: AsyncSession = Depends(get_session),
):
    req = body or RefreshRequest()
    if req.model not in COMPOSITE_MODELS:
        raise HTTPException(
            status_code=422, detail=f"Unknown model {req.model!r}"
        )
    accepted, payload = await observatory_service.trigger_refresh_job(
        session,
        model_id=req.model,
        collect_providers=req.collect_providers,
        sources=req.sources,
    )
    if not accepted:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "An observatory refresh or collection job is already running.",
                "job": payload,
            },
        )
    return payload
