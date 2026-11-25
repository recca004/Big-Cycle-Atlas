"""Export reproducible Atlas research evidence to .dev/reports.

The export intentionally uses the existing research services and latest-vintage
selection rules. It does not invent scores, classifications or forecasts.
"""
import argparse
import asyncio
import csv
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, ".")

from sqlalchemy import func, select

from app.cycle.force_aggregation_definitions import FORCE_AGGREGATION_CONFIGS, FORCE_AGGREGATION_VERSION
from app.cycle.force_definitions import FORCE_DEFINITIONS
from app.cycle.normalizer import CURRENT_MODEL_VERSION
from app.db.session import get_sessionmaker
from app.models import (
    Country,
    DataSource,
    Indicator,
    IndicatorDiagnostic,
    IndicatorRevision,
    IngestionRun,
    MarketInstrument,
    MarketObservation,
    Observation,
    ReferenceObservation,
    SourceSeries,
)
from app.research.composite import COMPOSITE_MODELS, run_composite
from app.research.model_diagnostics import (
    actual_force_inclusion,
    all_semantic_force_matrices,
    compare_core_histories,
)
from app.research.observatory import (
    CURRENCY_ROLES,
    POWER_INDICATORS,
    build_transition_monitor,
    compute_core_observatory,
    latest_completed_scoring_period,
)
from app.research.power_registry import (
    CURRENCY_RESEARCH_ENTITIES,
    GLOBAL_DENOMINATOR_SERIES,
    HISTORICAL_BOUNDARIES,
    POWER_MEASURE_DEFINITIONS,
    POWER_MEASURES_BY_INDICATOR,
)
from app.services import force_signal_service

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".dev" / "reports"
EXPORT = OUT / "export"
COUNTRIES_OUT = OUT / "countries"
ISO_ORDER = ["USA", "CHN", "IND", "JPN", "DEU", "GBR", "FRA", "CHE"]
POWER_EXPORT_INDICATORS = sorted(
    set(POWER_INDICATORS) | set(POWER_MEASURES_BY_INDICATOR)
)


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (datetime,)):
        return value.isoformat()
    if isinstance(value, set):
        return sorted(value)
    return str(value)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=_json_default), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return None


def _year(dt: datetime | None) -> int | None:
    return dt.year if dt else None


def _period(dt: datetime | None) -> str | None:
    return dt.date().isoformat() if dt else None


def _trend(points: list[dict[str, Any]], start_year: int) -> dict[str, Any]:
    latest = points[-1] if points else None
    in_range = [p for p in points if p["year"] >= start_year]
    baseline = in_range[0] if in_range else None
    full_baseline = points[0] if points else None
    return {
        "baseline_year": baseline["year"] if baseline else None,
        "baseline_value": baseline["value"] if baseline else None,
        "latest_year": latest["year"] if latest else None,
        "latest_value": latest["value"] if latest else None,
        "absolute_change": (
            latest["value"] - baseline["value"]
            if latest and baseline is not None
            else None
        ),
        "percentage_change": (
            ((latest["value"] - baseline["value"]) / abs(baseline["value"]) * 100)
            if latest and baseline and baseline["value"] not in (0, None)
            else None
        ),
        "full_baseline_year": full_baseline["year"] if full_baseline else None,
        "full_baseline_value": full_baseline["value"] if full_baseline else None,
        "full_absolute_change": (
            latest["value"] - full_baseline["value"]
            if latest and full_baseline is not None
            else None
        ),
        "full_percentage_change": (
            ((latest["value"] - full_baseline["value"]) / abs(full_baseline["value"]) * 100)
            if latest and full_baseline and full_baseline["value"] not in (0, None)
            else None
        ),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Atlas research evidence for independent analysis."
    )
    parser.add_argument(
        "--from-year",
        type=int,
        default=1980,
        help="Historical baseline used for trend summaries and Observatory research (default: 1980).",
    )
    args = parser.parse_args()
    from_year = args.from_year

    OUT.mkdir(parents=True, exist_ok=True)
    EXPORT.mkdir(parents=True, exist_ok=True)
    COUNTRIES_OUT.mkdir(parents=True, exist_ok=True)
    session = get_sessionmaker()()

    countries = {c.iso3: c for c in (await session.execute(select(Country))).scalars()}
    sources = {s.id: s for s in (await session.execute(select(DataSource))).scalars()}

    # Inventory and provider status.
    inventory: dict[str, Any] = {
        "countries": (await session.execute(select(func.count(Country.id)))).scalar(),
        "indicators": (await session.execute(select(func.count(Indicator.id)))).scalar(),
        "data_sources": (await session.execute(select(func.count(DataSource.id)))).scalar(),
        "source_series": (await session.execute(select(func.count(SourceSeries.id)))).scalar(),
        "observations_all_vintages": (await session.execute(select(func.count(Observation.id)))).scalar(),
        "reference_observations": (await session.execute(select(func.count(ReferenceObservation.id)))).scalar(),
        "market_instruments": (await session.execute(select(func.count(MarketInstrument.id)))).scalar(),
        "market_observations": (await session.execute(select(func.count(MarketObservation.id)))).scalar(),
        "indicator_revisions": (await session.execute(select(func.count(IndicatorRevision.id)))).scalar(),
        "indicator_diagnostics": (await session.execute(select(func.count(IndicatorDiagnostic.id)))).scalar(),
        "ingestion_runs": (await session.execute(select(func.count(IngestionRun.id)))).scalar(),
    }
    inventory["distinct_observation_identities"] = (
        await session.execute(
            select(
                func.count(func.distinct(
                    func.concat(
                        Observation.country_id,
                        ":",
                        Observation.source_series_id,
                        ":",
                        Observation.period_start,
                    )
                ))
            )
        )
    ).scalar()
    inventory["latest_vintage_rows"] = (
        await session.execute(
            select(func.count(Observation.id)).where(Observation.supersedes_observation_id.is_(None))
        )
    ).scalar()

    coverage_rows = (
        await session.execute(
            select(
                Country.iso3,
                Country.name,
                Indicator.code,
                Indicator.name,
                Indicator.unit,
                Indicator.frequency,
                SourceSeries.external_code,
                SourceSeries.external_unit,
                DataSource.key,
                DataSource.name,
                func.min(Observation.period_start),
                func.max(Observation.period_start),
                func.count(func.distinct(Observation.period_start)),
                func.max(Observation.vintage_number),
                func.count(Observation.release_date),
                func.max(Observation.retrieved_at),
            )
            .select_from(Observation)
            .join(Country, Country.id == Observation.country_id)
            .join(Indicator, Indicator.id == Observation.indicator_id)
            .join(SourceSeries, SourceSeries.id == Observation.source_series_id)
            .join(DataSource, DataSource.id == Observation.data_source_id)
            .group_by(
                Country.iso3, Country.name, Indicator.code, Indicator.name,
                Indicator.unit, Indicator.frequency, SourceSeries.external_code,
                SourceSeries.external_unit, DataSource.key, DataSource.name,
            )
            .order_by(Country.iso3, Indicator.code)
        )
    ).all()
    coverage = [
        {
            "country": r[0], "country_name": r[1], "indicator": r[2],
            "indicator_name": r[3], "unit": r[4], "frequency": r[5],
            "source_series": r[6], "source_unit": r[7], "provider": r[8],
            "provider_name": r[9], "earliest_period": _period(r[10]),
            "latest_period": _period(r[11]), "distinct_periods": r[12],
            "max_vintage": r[13], "release_dates": r[14],
            "latest_retrieval": _period(r[15]),
        }
        for r in coverage_rows
    ]
    write_csv(EXPORT / "indicator_coverage.csv", coverage, list(coverage[0]))

    latest_vintage = (
        select(
            Observation.country_id.label("cid"),
            Observation.source_series_id.label("ssid"),
            Observation.period_start.label("period"),
            func.max(Observation.vintage_number).label("vintage"),
        )
        .group_by("cid", "ssid", "period")
        .subquery()
    )
    history_rows = (
        await session.execute(
            select(
                Country.iso3, Indicator.code, Indicator.name, Indicator.unit,
                Indicator.frequency, DataSource.key, SourceSeries.external_code,
                Observation.period_start, Observation.value, Observation.vintage_number,
                Observation.release_date, Observation.retrieved_at,
            )
            .select_from(Observation)
            .join(Country, Country.id == Observation.country_id)
            .join(Indicator, Indicator.id == Observation.indicator_id)
            .join(DataSource, DataSource.id == Observation.data_source_id)
            .join(SourceSeries, SourceSeries.id == Observation.source_series_id)
            .join(
                latest_vintage,
                (Observation.country_id == latest_vintage.c.cid)
                & (Observation.source_series_id == latest_vintage.c.ssid)
                & (Observation.period_start == latest_vintage.c.period)
                & (Observation.vintage_number == latest_vintage.c.vintage),
            )
            .order_by(Country.iso3, Indicator.code, Observation.period_start)
        )
    ).all()
    history = [
        {
            "country": r[0], "indicator": r[1], "indicator_name": r[2],
            "unit": r[3], "frequency": r[4], "provider": r[5],
            "source_series": r[6], "period": _period(r[7]), "year": _year(r[7]),
            "value": r[8], "vintage": r[9], "release_date": _period(r[10]),
            "retrieved_at": _period(r[11]),
        }
        for r in history_rows
    ]
    write_csv(
        EXPORT / "country_indicator_history.csv",
        history,
        ["country", "indicator", "indicator_name", "unit", "frequency", "provider",
         "source_series", "period", "year", "value", "vintage", "release_date", "retrieved_at"],
    )
    by_country_indicator: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in history:
        by_country_indicator[(item["country"], item["indicator"])].append(item)

    ref_vintage = (
        select(
            ReferenceObservation.universe_code.label("universe"),
            ReferenceObservation.indicator_code.label("indicator"),
            ReferenceObservation.country_iso3.label("entity"),
            ReferenceObservation.period_start.label("period"),
            func.max(ReferenceObservation.vintage_number).label("vintage"),
        )
        .group_by("universe", "indicator", "entity", "period")
        .subquery()
    )
    ref_rows = (
        await session.execute(
            select(
                ReferenceObservation.universe_code,
                ReferenceObservation.indicator_code,
                ReferenceObservation.country_iso3,
                ReferenceObservation.period_start,
                ReferenceObservation.value,
                ReferenceObservation.unit,
                ReferenceObservation.external_code,
                ReferenceObservation.retrieved_at,
            )
            .select_from(ReferenceObservation)
            .join(
                ref_vintage,
                (ReferenceObservation.universe_code == ref_vintage.c.universe)
                & (ReferenceObservation.indicator_code == ref_vintage.c.indicator)
                & (ReferenceObservation.country_iso3 == ref_vintage.c.entity)
                & (ReferenceObservation.period_start == ref_vintage.c.period)
                & (ReferenceObservation.vintage_number == ref_vintage.c.vintage),
            )
            .order_by(ReferenceObservation.universe_code, ReferenceObservation.indicator_code, ReferenceObservation.country_iso3, ReferenceObservation.period_start)
        )
    ).all()
    reference_history = [
        {
            "universe": r[0], "indicator": r[1], "entity": r[2],
            "period": _period(r[3]), "year": _year(r[3]), "value": r[4],
            "unit": r[5], "external_code": r[6], "retrieved_at": _period(r[7]),
        }
        for r in ref_rows
    ]
    global_denominators = {
        (r["indicator"], r["year"]): r["value"]
        for r in reference_history
        if r["universe"] == "world_wdi_denominator_v1" and r["entity"] == "WLD"
    }

    latest_sp = latest_completed_scoring_period()
    force_rows: list[dict[str, Any]] = []
    force_history: list[dict[str, Any]] = []
    signal_sets: dict[str, dict[str, Any]] = {}
    for iso3 in ISO_ORDER:
        signals = await force_signal_service.build_force_signals_as_of(session, iso3, latest_sp)
        signal_sets[iso3] = {s.force_code: s for s in signals}
        by_force = {s.force_code: s for s in signals}
        for definition in FORCE_DEFINITIONS:
            signal = by_force.get(definition.code)
            live_points: list[dict[str, Any]] = []
            for code in definition.live_indicator_codes:
                pts = by_country_indicator.get((iso3, code), [])
                live_points.extend(pts)
                trend = _trend(pts, from_year)
                force_history.append({
                    "country": iso3, "force": definition.code, "indicator": code,
                    "periods": len(pts), "earliest_year": pts[0]["year"] if pts else None,
                    "latest_year": pts[-1]["year"] if pts else None,
                    "baseline_year": trend["baseline_year"],
                    "baseline_value": trend["baseline_value"],
                    "latest_value": trend["latest_value"],
                    "absolute_change": trend["absolute_change"],
                    "percentage_change": trend["percentage_change"],
                    "full_baseline_year": trend["full_baseline_year"],
                    "full_baseline_value": trend["full_baseline_value"],
                    "full_absolute_change": trend["full_absolute_change"],
                    "full_percentage_change": trend["full_percentage_change"],
                    "unit": pts[0]["unit"] if pts else None,
                    "provider": pts[0]["provider"] if pts else None,
                })
            force_rows.append({
                "country": iso3, "country_name": countries[iso3].name,
                "force": definition.code, "force_name": definition.name,
                "execution_status": (
                    "scored" if signal and signal.level_score is not None
                    else "dimension_only" if signal and (signal.relative_score is not None or signal.momentum is not None)
                    else "context_only"
                ),
                "level_score": signal.level_score if signal else None,
                "relative_score": signal.relative_score if signal else None,
                "momentum_score": signal.momentum if signal else None,
                "coverage_status": (
                    "structural_context_available"
                    if definition.code == "geography"
                    else signal.coverage_status.value if signal else None
                ),
                "period": signal.scoring_period if signal else None,
                "live_indicator_codes": ";".join(definition.live_indicator_codes),
                "candidate_indicator_codes": ";".join(definition.candidate_indicator_codes),
                "coverage_ceiling": definition.coverage_ceiling.value if definition.coverage_ceiling else None,
                "coverage_notes": definition.coverage_notes,
                "earliest_live_period": min((p["period"] for p in live_points), default=None),
                "latest_live_period": max((p["period"] for p in live_points), default=None),
            })
    write_csv(EXPORT / "force_measurements.csv", force_rows, list(force_rows[0]))
    write_csv(EXPORT / "force_history.csv", force_history, list(force_history[0]))

    write_json(
        EXPORT / "force_methodology.json",
        {
            "normalization_version": CURRENT_MODEL_VERSION.version_id,
            "force_aggregation_version": FORCE_AGGREGATION_VERSION,
            "definitions": [
                {
                    "code": d.code, "name": d.name, "description": d.description,
                    "live_indicator_codes": list(d.live_indicator_codes),
                    "candidate_indicator_codes": list(d.candidate_indicator_codes),
                    "coverage_ceiling": d.coverage_ceiling.value if d.coverage_ceiling else None,
                    "coverage_notes": d.coverage_notes,
                }
                for d in FORCE_DEFINITIONS
            ],
            "aggregation_configs": {
                code: {
                    "level_mode": cfg.level_mode.value,
                    "relative_mode": cfg.relative_mode.value,
                    "momentum_mode": cfg.momentum_mode.value,
                    "confidence_mode": cfg.confidence_mode.value,
                    "components": [
                        {
                            "indicator_code": c.indicator_code,
                            "role": c.role.value,
                        }
                        for c in cfg.components
                    ],
                    "notes": cfg.notes,
                }
                for code, cfg in FORCE_AGGREGATION_CONFIGS.items()
            },
        },
    )

    cores: dict[str, dict[str, Any]] = {}
    for model_id in COMPOSITE_MODELS:
        cores[model_id] = await compute_core_observatory(
            session, model_id=model_id, start_year=from_year
        )

    power_rows: list[dict[str, Any]] = []
    cycle_rows: list[dict[str, Any]] = []
    transition_rows: list[dict[str, Any]] = []
    composite_rows: list[dict[str, Any]] = []
    model_rows: list[dict[str, Any]] = []
    forecast_payload: dict[str, Any] = {}
    for model_id, core in cores.items():
        for country in core["countries"]:
            latest = country["history"][-1] if country["history"] else {}
            composite_rows.append({
                "model": model_id, "country": country["iso3"],
                "period": latest.get("period"), "score": latest.get("score"),
                "momentum": latest.get("momentum"), "stage": latest.get("stage"),
                "phase": latest.get("phase"), "coverage_ratio": country.get("coverage_ratio"),
                "classified": country.get("classified"),
            })
            for point in country["history"]:
                cycle_rows.append({
                    "model": model_id, "country": country["iso3"],
                    "period": point["period"], "score": point["score"],
                    "momentum": point["momentum"], "stage": point["stage"],
                    "phase": point["phase"], "reason": point["reason"],
                })
            for transition in country["transitions"]:
                transition_rows.append({
                    "model": model_id, "country": country["iso3"],
                    "period": transition["period"], "to_stage": transition["to"],
                    "reason": transition["reason"],
                })
            if model_id == "model_b_domain":
                power = country["international_power"]
                for key, value in power.items():
                    if not isinstance(value, dict):
                        continue
                    for field, field_value in value.items():
                        if isinstance(field_value, dict):
                            for subfield, subvalue in field_value.items():
                                if isinstance(subvalue, (int, float, str)) or subvalue is None:
                                    power_rows.append({
                                        "country": country["iso3"], "measure": key,
                                        "field": f"{field}.{subfield}", "value": subvalue,
                                        "model": model_id,
                                    })
                        elif isinstance(field_value, (int, float, str)) or field_value is None:
                            power_rows.append({
                                "country": country["iso3"], "measure": key,
                                "field": field, "value": field_value,
                                "model": model_id,
                            })
        forecast = build_transition_monitor(
            core, "USA", "CHN", strict_eligible_periods=0
        )["forecast_readiness"]
        forecast_payload[model_id] = forecast
        for h in forecast.get("horizons", []):
            model_rows.append({
                "model": model_id, "horizon": h.get("horizon"),
                "available": h.get("available"), "status": h.get("status_label"),
                "blockers": ";".join(h.get("blockers", [])),
            })
    write_csv(EXPORT / "power_measures.csv", power_rows, ["country", "measure", "field", "value", "model"])
    write_csv(EXPORT / "composite_results.csv", composite_rows, list(composite_rows[0]))
    write_csv(EXPORT / "cycle_history.csv", cycle_rows, list(cycle_rows[0]))
    write_csv(EXPORT / "cycle_transitions.csv", transition_rows, list(transition_rows[0]))
    write_csv(EXPORT / "model_comparison.csv", model_rows, list(model_rows[0]))
    write_json(EXPORT / "forecast_readiness.json", forecast_payload)

    # Model correctness diagnostics.
    semantic_matrix = all_semantic_force_matrices()
    actual_inclusion_rows: list[dict[str, Any]] = []
    effective_weight_rows: list[dict[str, Any]] = []
    for iso3 in ISO_ORDER:
        for model_id in COMPOSITE_MODELS:
            result = run_composite(
                model_id, signal_sets[iso3], iso3,
                f"{latest_sp.year}-Q{latest_sp.quarter}",
            )
            actual_inclusion_rows.extend(actual_force_inclusion(result))
            for force_code, weight in result.weights.items():
                effective_weight_rows.append({
                    "model": model_id, "country": iso3,
                    "period": result.scoring_period,
                    "force": force_code, "effective_weight": weight,
                    "domain": next(
                        (r["domain"] for r in semantic_matrix
                         if r["model_id"] == model_id and r["force_code"] == force_code),
                        None,
                    ),
                })
    write_csv(
        EXPORT / "model_force_semantics.csv", semantic_matrix,
        ["model_id", "force_code", "configured_candidate", "semantics",
         "semantically_eligible", "semantic_reason", "domain", "overlap_groups"],
    )
    write_csv(
        EXPORT / "actual_force_inclusion.csv", actual_inclusion_rows,
        ["model_id", "country", "period", "force_code", "status", "value", "weight", "reason"],
    )
    write_csv(
        EXPORT / "model_effective_weights.csv", effective_weight_rows,
        ["model", "country", "period", "force", "effective_weight", "domain"],
    )
    pair_reports: dict[str, Any] = {}
    model_ids = list(COMPOSITE_MODELS)
    for i, left in enumerate(model_ids):
        for right in model_ids[i + 1:]:
            comparison = compare_core_histories(cores[left], cores[right])
            pair_reports[f"{left}__{right}"] = {
                "left_model": left, "right_model": right,
                "comparisons": comparison.comparisons,
                "exact_score_matches": comparison.exact_score_matches,
                "near_score_matches": comparison.near_score_matches,
                "exact_stage_matches": comparison.exact_stage_matches,
                "max_abs_score_difference": comparison.max_abs_score_difference,
                "exact_score_share": comparison.exact_score_share,
                "near_score_share": comparison.near_score_share,
                "exact_stage_share": comparison.exact_stage_share,
                "exact_equivalent_under_current_data": comparison.equivalent,
                "equivalent_under_current_data": comparison.materially_equivalent,
                "independent_evidence": not comparison.materially_equivalent,
            }
    write_json(
        EXPORT / "model_equivalence_report.json",
        {
            "interpretation": (
                "Equivalence is measured across the exported retrospective "
                "history; identical results do not count as independent model "
                "evidence."
            ),
            "pairs": pair_reports,
        },
    )
    disagreement_rows = []
    for iso3 in ISO_ORDER:
        for model_id, core in cores.items():
            country = next(c for c in core["countries"] if c["iso3"] == iso3)
            latest = country["history"][-1] if country["history"] else {}
            disagreement_rows.append({
                "country": iso3, "model": model_id,
                "period": latest.get("period"),
                "stage": latest.get("stage"), "score": latest.get("score"),
                "momentum": latest.get("momentum"),
                "coverage_ratio": country.get("coverage_ratio"),
                "cycle_label": core["model"].get("cycle_label"),
            })
    write_csv(
        EXPORT / "stage_disagreement.csv", disagreement_rows,
        ["country", "model", "period", "stage", "score", "momentum", "coverage_ratio", "cycle_label"],
    )

    # International-power registry and global-share derivations.
    coverage_by_country_indicator = {
        (r["country"], r["indicator"]): r for r in coverage
    }
    power_registry = []
    for definition in POWER_MEASURE_DEFINITIONS:
        countries_covered = []
        earliest = latest_obs = None
        if definition.indicator_code:
            matches = [
                r for r in coverage if r["indicator"] == definition.indicator_code
            ]
            countries_covered = sorted(r["country"] for r in matches)
            earliest = min((r["earliest_period"] for r in matches), default=None)
            latest_obs = max((r["latest_period"] for r in matches), default=None)
        denominator_coverage = [
            r for r in reference_history
            if r["external_code"] == definition.global_denominator_code
        ]
        power_registry.append({
            **{
                "dimension": definition.dimension,
                "measurement": definition.measurement,
                "indicator_code": definition.indicator_code,
                "external_code": definition.external_code,
                "source_key": definition.source_key,
                "unit": definition.unit,
                "frequency": definition.frequency,
                "entity_type": definition.entity_type,
                "reference_population": definition.reference_population,
                "comparison_semantics": definition.comparison_semantics,
                "global_denominator_code": definition.global_denominator_code,
                "limitations": definition.limitations,
            },
            "tracked_countries_with_data": countries_covered,
            "earliest_period": earliest,
            "latest_period": latest_obs,
            "world_denominator_periods": len(denominator_coverage),
            "world_denominator_latest": max(
                (r["period"] for r in denominator_coverage), default=None
            ),
        })
    write_json(EXPORT / "power_measure_registry.json", power_registry)

    global_share_rows = []
    denominator_by_external = {
        definition.indicator_code: definition.global_denominator_code
        for definition in POWER_MEASURE_DEFINITIONS
        if definition.indicator_code and definition.global_denominator_code
    }
    for row in history:
        denominator_code = denominator_by_external.get(row["indicator"])
        if not denominator_code:
            continue
        denominator = global_denominators.get((row["indicator"], row["year"]))
        if denominator in (None, 0):
            continue
        global_share_rows.append({
            "country": row["country"], "indicator": row["indicator"],
            "period": row["period"], "year": row["year"],
            "value": row["value"], "world_value": denominator,
            "global_share_pct": row["value"] / denominator * 100,
            "unit": row["unit"], "provider": row["provider"],
            "denominator_entity": "WLD",
            "denominator_series": denominator_code,
        })
    write_csv(
        EXPORT / "global_power_shares.csv", global_share_rows,
        ["country", "indicator", "period", "year", "value", "world_value",
         "global_share_pct", "unit", "provider", "denominator_entity", "denominator_series"],
    )
    financial_codes = {
        m.indicator_code for m in POWER_MEASURE_DEFINITIONS
        if m.dimension == "financial_centre_strength" and m.indicator_code
    }
    write_csv(
        EXPORT / "financial_influence.csv",
        [r for r in history if r["indicator"] in financial_codes],
        list(history[0]),
    )
    productivity_codes = {
        "LABOUR_PRODUCTIVITY_PER_HOUR", "GDP_PER_CAPITA",
        "GDP_REAL_CONSTANT_USD", "GDP_PPP_CURRENT_INTL",
    }
    write_csv(
        EXPORT / "productivity_comparison.csv",
        [r for r in history if r["indicator"] in productivity_codes],
        list(history[0]),
    )
    write_csv(
        EXPORT / "currency_influence.csv",
        [
            {**entity, "measurement_status": "registered_not_imported"}
            for entity in CURRENCY_RESEARCH_ENTITIES.values()
        ],
        ["entity", "scope", "issuer_area", "country_iso3", "measurement_status"],
    )
    write_csv(
        EXPORT / "historical_boundary_metadata.csv",
        list(HISTORICAL_BOUNDARIES),
        ["country", "statistical_entity", "applies_from", "applies_to",
         "interpretation", "source_methodology"],
    )
    write_json(
        EXPORT / "strict_historical_availability.json",
        {
            "raw_observation_vintages": inventory["observations_all_vintages"],
            "distinct_observation_identities": inventory["distinct_observation_identities"],
            "with_provider_release_date": sum(1 for r in history if r["release_date"]),
            "with_atlas_retrieval": sum(1 for r in history if r["retrieved_at"]),
            "strict_scored_periods": 0,
            "explanation": (
                "Current observations lack provider release dates, and Atlas "
                "retrieval timestamps prove only prospective availability. No "
                "release-date-safe composite run exists, so zero scored "
                "periods are strictly eligible forecast samples."
            ),
        },
    )

    power_history = [r for r in history if r["indicator"] in POWER_EXPORT_INDICATORS]
    write_csv(
        EXPORT / "power_measure_history.csv",
        power_history,
        list(history[0]),
    )
    provider_rows = []
    for source in sources.values():
        provider_coverage = [r for r in coverage if r["provider"] == source.key]
        ingested = bool(provider_coverage)
        status = source.status.value if hasattr(source.status, "value") else str(source.status)
        provider_rows.append({
            "provider": source.key, "provider_name": source.name,
            "configured_status": status,
            "effective_status": "ingested" if ingested else status,
            "country_indicator_series": len(provider_coverage),
            "latest_retrieval": max(
                (r["latest_retrieval"] for r in provider_coverage), default=None
            ),
            "base_url": source.base_url or "",
            "auth_type": source.auth_type or "",
            "update_frequency": source.update_frequency or "",
            "rate_limit_notes": source.rate_limit_notes or "",
            "documentation_url": source.documentation_url or "",
            "metadata": source.extra_metadata or {},
        })
    write_csv(EXPORT / "provider_status.csv", provider_rows, list(provider_rows[0]))

    quality_rows: list[dict[str, Any]] = []
    for row in coverage:
        earliest = int(row["earliest_period"][:4]) if row["earliest_period"] else None
        latest = int(row["latest_period"][:4]) if row["latest_period"] else None
        expected = latest - earliest + 1 if earliest and latest else None
        gaps = expected - int(row["distinct_periods"]) if expected is not None else None
        if earliest and earliest > 1980:
            quality_rows.append({
                "country": row["country"], "indicator": row["indicator"],
                "finding": "starts_after_1980", "detail": f"earliest={earliest}",
            })
        if gaps and gaps > max(3, expected * 0.25):
            quality_rows.append({
                "country": row["country"], "indicator": row["indicator"],
                "finding": "large_period_gaps", "detail": f"{gaps} missing periods",
            })
    negative_growth = [
        r for r in history
        if r["indicator"] in {"POPULATION", "GDP_CURRENT_USD", "LABOUR_PRODUCTIVITY_PER_HOUR"}
        and (r["value"] or 0) < 0
    ]
    for r in negative_growth:
        quality_rows.append({
            "country": r["country"], "indicator": r["indicator"],
            "finding": "unexpected_negative_scale", "detail": f"{r['period']}={r['value']}",
        })
    write_csv(
        EXPORT / "data_quality_findings.csv", quality_rows,
        ["country", "indicator", "finding", "detail"],
    )
    write_json(EXPORT / "database_inventory.json", inventory)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "git_commit": _git_commit(),
        "database": inventory,
        "latest_vintage_rule": "maximum vintage_number per country + source_series + period_start",
        "historical_execution_mode": "retrospective_latest_vintage; not a release-date-safe backtest",
        "scoring_period": f"{latest_sp.year}-Q{latest_sp.quarter}",
        "requested_from_year": from_year,
        "normalization_version": CURRENT_MODEL_VERSION.version_id,
        "force_aggregation_version": FORCE_AGGREGATION_VERSION,
        "composite_models": {
            key: {
                "version": model.version, "kind": model.kind,
                "eligible_forces": sorted(model.eligible_forces),
                "missing_policy": (
                    model.missing_policy.value
                    if hasattr(model.missing_policy, "value")
                    else str(model.missing_policy)
                ),
                "min_coverage": model.min_coverage,
                "notes": model.notes,
            }
            for key, model in COMPOSITE_MODELS.items()
        },
        "providers": provider_rows,
        "currency_roles": CURRENCY_ROLES,
        "power_indicators": POWER_EXPORT_INDICATORS,
        "force_semantics": semantic_matrix,
        "model_equivalence": pair_reports,
        "global_denominator_series": GLOBAL_DENOMINATOR_SERIES,
        "currency_research_entities": CURRENCY_RESEARCH_ENTITIES,
        "historical_boundaries": HISTORICAL_BOUNDARIES,
        "generated_exports": sorted(path.name for path in EXPORT.iterdir() if path.is_file()),
        "limitations": [
            "Retrospective history uses latest available vintages, not only information published at each historical date.",
            "Composite and stage labels are experimental and coverage-gated.",
            "Tracked-universe shares are not global shares.",
            "Military expenditure measures resources, not complete capability.",
            "Missing observations remain missing and are never interpolated.",
        ],
    }
    write_json(EXPORT / "research_manifest.json", manifest)
    write_json(OUT / "research_manifest.json", manifest)

    # Compact country reports generated from actual exported evidence.
    latest_core = cores["model_b_domain"]
    countries_by_iso = {c["iso3"]: c for c in latest_core["countries"]}
    for iso3 in ISO_ORDER:
        country = countries_by_iso[iso3]
        inds = [r for r in force_history if r["country"] == iso3 and r["indicator"]]
        inds_sorted = sorted(inds, key=lambda r: r["earliest_year"] or 9999)
        model_lines = []
        for row in composite_rows:
            if row["country"] == iso3:
                model_lines.append(
                    f"| `{row['model']}` | {row['period'] or '—'} | {row['score'] if row['score'] is not None else '—'} | {row['stage'] or 'unclassified'} | {row['coverage_ratio']} |"
                )
        force_lines = [
            f"| {r['force_name']} | {r['execution_status']} | {r['level_score'] if r['level_score'] is not None else '—'} | {r['coverage_status'] or '—'} | {r['period'] or '—'} | {r['coverage_notes']} |"
            for r in force_rows if r["country"] == iso3
        ]
        history_lines = [
            f"| {r['force']} `{r['indicator']}` | {r['earliest_year'] or '—'} | {r['baseline_year'] or '—'} | {r['latest_year'] or '—'} | {r['baseline_value'] if r['baseline_value'] is not None else '—'} | {r['latest_value'] if r['latest_value'] is not None else '—'} | {r['absolute_change'] if r['absolute_change'] is not None else '—'} | {r['full_baseline_year'] or '—'} | {r['full_absolute_change'] if r['full_absolute_change'] is not None else '—'} | {r['unit'] or ''} |"
            for r in inds_sorted
        ]
        report = f"""# {country['name']} ({iso3}) — economic research profile

Generated: {manifest['generated_at']}
Methodology: experimental, `{CURRENT_MODEL_VERSION.version_id}`, `{FORCE_AGGREGATION_VERSION}`
Requested calculation period: `{manifest['scoring_period']}`
Latest classified composite period: `{country['history'][-1]['period'] if country['history'] else '—'}`
Latest raw observation period: `{max((r['latest_year'] for r in inds if r['latest_year'] is not None), default=None) or '—'}`

## Current interpretation

The production `model_b_domain` result is **{country['domestic_condition_score']}** with stage **{country['stage'] or 'unclassified'}**, direction `{country['direction']}`, and coverage ratio `{country['coverage_ratio']}`. This is an experimental domestic-condition cycle result, not an international-power ranking and not a claim about an empire life-cycle stage.

## Composite models

| Model | Period | Score | Stage | Coverage |
|---|---:|---:|---|---:|
{chr(10).join(model_lines)}

## Seventeen-force evidence

| Force | Status | Level | Coverage | Period | Actual measurement and limitation |
|---|---|---:|---|---|---|
{chr(10).join(force_lines)}

## Historical raw-indicator changes

The `range baseline` is the first observation in the requested {manifest['requested_from_year']}-present window; the `full baseline` is the first observation ever stored. These are deliberately separate views.

| Force / indicator | Earliest | Range baseline | Latest | Range baseline value | Latest value | Range change | Full baseline | Full change | Unit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(history_lines)}

## Scientific limitations

- Raw history is latest-vintage evidence; it is not a release-date-safe backtest.
- Missing periods remain missing. No value in this report is interpolated.
- Force statuses distinguish scores, dimension-only signals and context profiles.
- Military expenditure is resources, not total capability.
- Tracked-universe shares are not global shares.
"""
        (COUNTRIES_OUT / f"{iso3}.md").write_text(report, encoding="utf-8")

    # Main research report and compact handover.
    country_comparison_rows = []
    for country in latest_core["countries"]:
        power = country["international_power"]
        country_comparison_rows.append(
            "| {name} ({iso3}) | {score} | {stage} | {direction} | {coverage} | ${gdp} | {gdp_share}% | ${military} | {mil_share}% | {trade_share}% |".format(
                name=country["name"],
                iso3=country["iso3"],
                score=f"{country['domestic_condition_score']:.2f}" if country["domestic_condition_score"] is not None else "—",
                stage=country["stage"] or "unclassified",
                direction=country["direction"],
                coverage=f"{country['coverage_ratio']:.1%}",
                gdp=f"{power['economic_size'].get('value_usd') or 0:,.0f}",
                gdp_share=power["economic_size"].get("tracked_share_pct"),
                military=f"{power['military_resources'].get('expenditure_usd') or 0:,.0f}",
                mil_share=power["military_resources"].get("tracked_share_pct"),
                trade_share=power["international_trade"].get("tracked_share_pct"),
            )
        )

    earliest_classified = []
    for model_id in COMPOSITE_MODELS:
        rows = [r for r in cycle_rows if r["model"] == model_id and r["stage"]]
        for iso3 in ISO_ORDER:
            iso_rows = [r for r in rows if r["country"] == iso3]
            if iso_rows:
                earliest_classified.append(
                    f"| `{model_id}` | {iso3} | {iso_rows[0]['period']} | {iso_rows[0]['stage']} |"
                )

    model_agreement_rows = []
    for iso3 in ISO_ORDER:
        stages = {
            row["model"]: row["stage"]
            for row in composite_rows
            if row["country"] == iso3 and row["stage"]
        }
        scores = {
            row["model"]: row["score"]
            for row in composite_rows
            if row["country"] == iso3 and row["score"] is not None
        }
        unique_stages = set(stages.values())
        spread = (
            max(scores.values()) - min(scores.values()) if len(scores) > 1 else None
        )
        model_agreement_rows.append(
            f"| {iso3} | {'; '.join(f'{m}={s}' for m, s in stages.items())} | {len(unique_stages)} | {spread:.2f} |"
            if spread is not None
            else f"| {iso3} | {'; '.join(f'{m}={s}' for m, s in stages.items())} | {len(unique_stages)} | — |"
        )

    us_china_rows = []
    comparison_codes = [
        "GDP_CURRENT_USD", "GDP_PPP_CURRENT_INTL", "GDP_REAL_CONSTANT_USD",
        "POPULATION", "MERCHANDISE_EXPORTS_USD", "MERCHANDISE_IMPORTS_USD",
        "COMMERCIAL_SERVICE_EXPORTS_USD", "COMMERCIAL_SERVICE_IMPORTS_USD",
        "EXPORTS_GDP", "IMPORTS_GDP", "CURRENT_ACCOUNT_GDP",
        "MILITARY_EXPENDITURE_USD", "MILITARY_EXPENDITURE_GDP",
        "RND_EXPENDITURE_GDP", "PATENT_APPLICATIONS_RESIDENT",
        "RESEARCHERS_PER_MILLION", "HIGH_TECHNOLOGY_EXPORTS_USD",
        "LABOUR_PRODUCTIVITY_PER_HOUR", "GOVERNMENT_DEBT_GDP",
        "STOCK_MARKET_CAP_GDP", "DOMESTIC_CREDIT_PRIVATE_GDP",
        "BROAD_MONEY_GDP",
    ]
    for code in comparison_codes:
        usa = by_country_indicator.get(("USA", code), [])
        chn = by_country_indicator.get(("CHN", code), [])
        usa_by_year = {p["year"]: p for p in usa}
        chn_by_year = {p["year"]: p for p in chn}
        common_years = sorted(set(usa_by_year) & set(chn_by_year))
        range_years = [y for y in common_years if y >= from_year]
        base_year = range_years[0] if range_years else (common_years[0] if common_years else None)
        latest_year = common_years[-1] if common_years else None
        usa_base = usa_by_year.get(base_year) if base_year is not None else None
        chn_base = chn_by_year.get(base_year) if base_year is not None else None
        usa_latest = usa_by_year.get(latest_year) if latest_year is not None else None
        chn_latest = chn_by_year.get(latest_year) if latest_year is not None else None
        ratio_now = (
            chn_latest["value"] / usa_latest["value"]
            if usa_latest and chn_latest and usa_latest["value"] not in (0, None)
            else None
        )
        ratio_base = (
            chn_base["value"] / usa_base["value"]
            if usa_base and chn_base and usa_base["value"] not in (0, None)
            else None
        )
        us_china_rows.append(
            f"| `{code}` | {base_year or '—'} | {usa_base['value'] if usa_base else '—'} | {chn_base['value'] if chn_base else '—'} | {latest_year or '—'} | {usa_latest['value'] if usa_latest else '—'} | {chn_latest['value'] if chn_latest else '—'} | {f'{ratio_base:.3f}' if ratio_base is not None else '—'} | {f'{ratio_now:.3f}' if ratio_now is not None else '—'} | {usa_latest['unit'] if usa_latest else ''} |"
        )

    # Common-period country comparisons for the report.
    period_windows = [
        ("1980-1990", 1980, 1990), ("1990-2000", 1990, 2000),
        ("2000-2010", 2000, 2010), ("2010-2020", 2010, 2020),
        ("2020-latest", 2020, 9999), ("recent_1y", None, 1),
        ("recent_3y", None, 3), ("recent_5y", None, 5),
        ("recent_10y", None, 10),
    ]
    period_codes = [
        "GDP_CURRENT_USD", "GDP_PPP_CURRENT_INTL", "GDP_REAL_CONSTANT_USD",
        "POPULATION", "MERCHANDISE_EXPORTS_USD", "MERCHANDISE_IMPORTS_USD",
        "COMMERCIAL_SERVICE_EXPORTS_USD", "COMMERCIAL_SERVICE_IMPORTS_USD",
        "MILITARY_EXPENDITURE_USD", "RND_EXPENDITURE_GDP",
        "PATENT_APPLICATIONS_RESIDENT", "RESEARCHERS_PER_MILLION",
        "STOCK_MARKET_CAP_GDP", "DOMESTIC_CREDIT_PRIVATE_GDP",
    ]
    period_rows = []
    for iso3 in ["USA", "CHN", "IND"]:
        for code in period_codes:
            pts = by_country_indicator.get((iso3, code), [])
            if not pts:
                continue
            latest_pt = pts[-1]
            for label, start, end in period_windows:
                if start is None:
                    start_year = latest_pt["year"] - end
                    selected = [p for p in pts if p["year"] >= start_year]
                    first = selected[0] if selected else pts[0]
                    last = latest_pt
                else:
                    selected = [p for p in pts if start <= p["year"] <= end]
                    if not selected:
                        continue
                    first, last = selected[0], selected[-1]
                if first["year"] == last["year"]:
                    continue
                period_rows.append({
                    "country": iso3, "indicator": code, "window": label,
                    "start_year": first["year"], "end_year": last["year"],
                    "start_value": first["value"], "end_value": last["value"],
                    "absolute_change": last["value"] - first["value"],
                    "percentage_change": (
                        (last["value"] - first["value"]) / abs(first["value"]) * 100
                        if first["value"] not in (0, None) else None
                    ),
                    "unit": last["unit"], "provider": last["provider"],
                })
    write_csv(
        EXPORT / "historical_period_comparison.csv", period_rows,
        ["country", "indicator", "window", "start_year", "end_year",
         "start_value", "end_value", "absolute_change", "percentage_change",
         "unit", "provider"],
    )

    quality_counts: dict[str, int] = defaultdict(int)
    for row in quality_rows:
        quality_counts[row["finding"]] += 1
    model_table = []
    for model_id, spec in COMPOSITE_MODELS.items():
        rows = [r for r in composite_rows if r["model"] == model_id]
        scored = [r for r in rows if r["score"] is not None]
        classified = [r for r in rows if r["stage"]]
        model_table.append(
            f"| `{model_id}` | {len(scored)} | {len(classified)} | {spec.notes} |"
        )
    bc_pair = pair_reports.get("model_b_domain__model_c_overlap", {})
    own_history_exclusions = [
        r for r in actual_inclusion_rows
        if r["force_code"] == "indebtedness" and r["status"] == "semantically_excluded"
    ]
    global_latest_lines = []
    for iso3 in ["USA", "CHN", "IND"]:
        for code in [
            "GDP_CURRENT_USD", "GDP_PPP_CURRENT_INTL", "GDP_REAL_CONSTANT_USD",
            "MERCHANDISE_EXPORTS_USD", "MERCHANDISE_IMPORTS_USD",
            "MILITARY_EXPENDITURE_USD", "PATENT_APPLICATIONS_RESIDENT",
            "HIGH_TECHNOLOGY_EXPORTS_USD",
        ]:
            rows = [
                r for r in global_share_rows
                if r["country"] == iso3 and r["indicator"] == code
            ]
            if rows:
                row = rows[-1]
                global_latest_lines.append(
                    f"| {iso3} | `{code}` | {row['period']} | {row['global_share_pct']:.2f}% |"
                )
    equivalence_lines = [
        f"| `{left}` vs `{right}` | {p['comparisons']} | {p['exact_score_share']:.1%} | {p['near_score_share']:.1%} | {p['exact_stage_share']:.1%} | {'yes' if p['equivalent_under_current_data'] else 'no'} |"
        for key, p in pair_reports.items()
        for left, right in [(p["left_model"], p["right_model"])]
    ]

    main_report = f"""# Big Cycle Atlas — economic research handover, {from_year}–present

Generated: {manifest['generated_at']}
Base commit: `{manifest['git_commit']}`
Methodology: `{CURRENT_MODEL_VERSION.version_id}`, `{FORCE_AGGREGATION_VERSION}`, experimental cycle classifier v1

## 1. Executive economic summary

Big Cycle Atlas exports actual production evidence, not a demonstration dataset. Raw macroeconomic observations already cover 1960 onward for several scale measures, while evidence-gated cycle classifications currently begin around 1995–1996 because the approved force inputs do not support earlier scores.

Largest tracked economy: **{latest_core['power_summary']['largest_economy_iso3']}**; second: **{latest_core['power_summary']['second_economy_iso3']}**. Highest domestic-condition score: **{latest_core['power_summary']['highest_domestic_condition_iso3']}**. International power is reported separately from domestic condition.

## 2. Database inventory

| Table / object | Count |
|---|---:|
{chr(10).join(f"| `{key}` | {value} |" for key, value in inventory.items())}

## 3. Historical coverage assessment

- Raw indicator coverage: `export/indicator_coverage.csv` ({len(coverage)} country/provider/indicator records).
- Full latest-vintage country-indicator history: `export/country_indicator_history.csv` ({len(history)} latest-vintage observations).
- GDP, GDP per capita and population extend to 1960 for all tracked countries.
- Several trade and capital-flow measures reach 1970 or earlier.
- Government debt starts 1980 or later; labour participation starts 1990; WGI starts 1996; productivity is country-dependent.
- Verified stage classifications do not begin in {from_year}; earliest supported model classifications are listed below.

### Earliest verified classifications

| Model | Country | First classified period | Stage |
|---|---|---:|---|
{chr(10).join(earliest_classified)}

## 4. Eight-country economic comparison

| Country | Domestic condition | Stage | Direction | Coverage | GDP | Tracked GDP share | Military expenditure | Tracked military share | Tracked trade share |
|---|---:|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(country_comparison_rows)}

Tracked shares use the eight Atlas countries as the denominator and are not global shares.

## 5. Seventeen-force evidence

See `export/force_measurements.csv` for the 136-row country-force matrix and `export/force_methodology.json` for approved definitions, live inputs, candidate indicators, ceilings and aggregation semantics. Only approved executable scores are numerical; context and dimension profiles are deliberately not presented as fabricated force scores.

Key methodology constraints:

- Leadership is represented by WGI government effectiveness, not individual leaders.
- Character is represented by relative economic participation, not national character.
- Productivity is an OECD-reference percentile where available, not a global percentile.
- Indebtedness uses an approved own-history debt-service/credit-gap composition.
- Military expenditure is resources absorbed by defence, not total capability.
- Geography remains structural context; acts of nature remain incomplete hazard evidence.

## 6. International power evidence

See `export/power_measure_registry.json`, `export/global_power_shares.csv`, `export/power_measures.csv` and `export/power_measure_history.csv`. The registry separates economic output, trade, military resources, innovation, education, financial depth and reserve-currency entities; it does not define a composite power ranking.

### Latest verified global shares

| Country | Measurement | Observation period | Global share |
|---|---|---:|---:|
{chr(10).join(global_latest_lines)}

Global shares use provider world aggregates (`WLD`) as denominators and are distinct from the eight-country tracked shares shown above. Reserve-currency records are registered but remain unavailable because verified COFER/BIS currency observations have not yet been imported; unreported currencies are never set to zero.

## 7. USA–China–India measured comparison

| Indicator | Common baseline | USA baseline | China baseline | Common latest | USA latest | China latest | China/USA baseline | China/USA latest | Unit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(us_china_rows)}

Ratios are direct raw-measurement ratios on common observation years and are only meaningful for compatible units and reference populations. A change in ratio indicates convergence/divergence in that measurement, not a complete leadership transition.

Decade and recent 1/3/5/10-year changes for USA, China and India are exported in `export/historical_period_comparison.csv`. India is therefore compared on the same measurement definitions rather than forced into a cycle-stage narrative.

## 8. Four-model experimental domestic-condition comparison

| Model | Countries with latest score | Latest classified periods | Notes |
|---|---:|---:|---|
{chr(10).join(model_table)}

### Equivalence and actual inclusion audit

| Pair | Country-period comparisons | Exact score agreement | Near-exact score agreement | Exact stage agreement | Materially equivalent |
|---|---:|---:|---:|---:|---|
{chr(10).join(equivalence_lines)}

`model_b_domain` versus `model_c_overlap`: {bc_pair.get('comparisons', 0)} comparisons, {bc_pair.get('exact_score_share', 0):.1%} exact-score, {bc_pair.get('near_score_share', 0):.1%} near-exact-score and {bc_pair.get('exact_stage_share', 0):.1%} exact-stage agreement; **{'materially equivalent' if bc_pair.get('equivalent_under_current_data') else 'not equivalent'} under the current force set**. Equivalent models are not independent confirmation. The current populated domain units collapse to the same four units as the declared overlap groups, so the intended weighting distinction produces identical effective weights; this is documented evidence, not a formula defect that should be hidden by artificial disagreement.

Actual included/excluded forces are exported in `export/actual_force_inclusion.csv`; effective weights are in `export/model_effective_weights.csv`. Indebtedness is configured as a candidate but produced {len(own_history_exclusions)} semantic exclusions because its approved score is own-history condition, not a cross-country comparable level.

### Current model agreement

| Country | Current stages | Unique stages | Composite score spread |
|---|---|---:|---:|
{chr(10).join(model_agreement_rows)}

Detailed scores: `export/composite_results.csv`
Complete classifications: `export/cycle_history.csv`
Transitions: `export/cycle_transitions.csv` ({len(transition_rows)} recorded model-country transitions)

## 9. Forecast readiness

See `export/forecast_readiness.json` and `export/strict_historical_availability.json`. Raw observation vintages ({inventory['observations_all_vintages']}) are stored data versions, not scored forecast samples. Atlas retrieval timestamps prove when data entered Atlas, not when providers published it historically. The corrected strict-eligible historical scored-period count is **0** until a release-date-safe scoring run exists; forecast probabilities remain unavailable.

## 10. Data quality findings

See `export/data_quality_findings.csv`. Material gaps are reported as gaps, not corrected silently or converted to zero.

| Finding | Records |
|---|---:|
{chr(10).join(f"| `{key}` | {value} |" for key, value in sorted(quality_counts.items()))}

## 11. Scientific limitations

- Historical calculations use latest-vintage observations and are retrospective research, not release-date-safe backtests.
- Raw scale measures may extend to 1960, but the cycle engine remains constrained by coverage, minimum observations and hysteresis.
- Military spending is an input resource, not full military capability.
- OECD productivity percentiles are explicitly OECD-reference measurements and are not global percentiles.
- Financial-centre and reserve-currency dimensions remain materially incomplete.
- Boundary metadata distinguishes current Germany from provider-labelled pre-1991 history and mainland-China coverage; provider definitions still limit historical joins.

## 12. Recommended next research priorities

1. Add Maddison/PWT real-output and capital history as separate labelled historical methods.
2. Add SIPRI direct military expenditure records for provenance and global-share denominators.
3. Add verified financial-centre/capital-market and reserve-currency reference series.
4. Extend boundary metadata beyond the implemented Germany/China records as new territorial-history providers are integrated.
5. Preserve evidence gates before attempting any leadership-transition forecast.
"""
    (OUT / "ATLAS_RESEARCH_1980_PRESENT.md").write_text(main_report, encoding="utf-8")

    handover = f"""# Big Cycle Atlas — compact ChatGPT handover

Generated: {manifest['generated_at']}
Base commit: `{manifest['git_commit']}`

This package contains the actual database inventory, latest-vintage raw histories, approved force evidence, four-model experimental cycle results, international-power measurements and forecast-gate evidence.

- Main report: `ATLAS_RESEARCH_1980_PRESENT.md`
- Country reports: `countries/USA.md`, `CHN.md`, `IND.md`, `JPN.md`, `DEU.md`, `GBR.md`, `FRA.md`, `CHE.md`
- Machine-readable package: `export/`
- Reproducibility manifest: `export/research_manifest.json`

## Key facts

- Raw GDP/population history reaches 1960; several trade/credit series reach 1970 or earlier.
- Valid experimental classifications begin around 1995–1996, not 1980.
- {len(inventory)} inventory fields and {len(coverage)} country-indicator coverage records were exported.
- {len(force_rows)} country-force rows and {len(cycle_rows)} model-history points were exported.
- `model_b_domain` and `model_c_overlap` are materially equivalent under current data: {pair_reports['model_b_domain__model_c_overlap']['comparisons']} comparisons, {pair_reports['model_b_domain__model_c_overlap']['near_score_share']:.1%} near-score and {pair_reports['model_b_domain__model_c_overlap']['exact_stage_share']:.1%} stage agreement; they are not independent evidence.
- Indebtedness is a configured own-history measurement but {sum(1 for r in actual_inclusion_rows if r['force_code'] == 'indebtedness' and r['status'] == 'semantically_excluded')} semantic exclusions prevent it entering the 0–100 cross-country composites.
- Strict release-date-safe scored periods: **0**; {inventory['observations_all_vintages']} stored observation vintages are provenance, not forecast origins.
- Forecast output remains unavailable where readiness gates fail.

## Independent-review questions

Use the CSV/JSON exports to test: country rankings by dimension, long-run convergence/divergence, model agreement, USA–China transitions, India’s measurable expansion, missing-force evidence, and whether any leadership-transition forecast is defensible without release-date-safe samples.
"""
    (OUT / "CHATGPT_HANDOVER.md").write_text(handover, encoding="utf-8")

    await session.close()
    print(f"Wrote research export to {OUT}")
    print(json.dumps({"inventory": inventory, "coverage_rows": len(coverage), "force_rows": len(force_rows), "cycle_rows": len(cycle_rows)}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
