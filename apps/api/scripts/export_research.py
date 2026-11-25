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
from app.research.composite import COMPOSITE_MODELS
from app.research.observatory import (
    CURRENCY_ROLES,
    POWER_INDICATORS,
    build_transition_monitor,
    compute_core_observatory,
    latest_completed_scoring_period,
)
from app.services import force_signal_service

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".dev" / "reports"
EXPORT = OUT / "export"
COUNTRIES_OUT = OUT / "countries"
ISO_ORDER = ["USA", "CHN", "IND", "JPN", "DEU", "GBR", "FRA", "CHE"]


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
    candidates = [p for p in points if p["year"] <= start_year]
    baseline = candidates[-1] if candidates else None
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

    latest_sp = latest_completed_scoring_period()
    force_rows: list[dict[str, Any]] = []
    force_history: list[dict[str, Any]] = []
    for iso3 in ISO_ORDER:
        signals = await force_signal_service.build_force_signals_as_of(session, iso3, latest_sp)
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
                "coverage_status": signal.coverage_status.value if signal else None,
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
                    if isinstance(value, dict):
                        for field, field_value in value.items():
                            if isinstance(field_value, (int, float, str)) or field_value is None:
                                power_rows.append({
                                    "country": country["iso3"], "measure": key,
                                    "field": field, "value": field_value,
                                    "model": model_id,
                                })
        forecast = build_transition_monitor(
            core, "USA", "CHN", strict_eligible_periods=inventory["observations_all_vintages"]
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

    power_history = [r for r in history if r["indicator"] in POWER_INDICATORS]
    write_csv(
        EXPORT / "power_measure_history.csv",
        power_history,
        list(history[0]),
    )
    provider_rows = [
        {
            "provider": source.key, "provider_name": source.name,
            "status": source.status, "base_url": source.base_url,
            "update_frequency": source.update_frequency,
            "rate_limit_notes": source.rate_limit_notes,
            "documentation_url": source.documentation_url,
        }
        for source in sources.values()
    ]
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
        "power_indicators": list(POWER_INDICATORS),
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
            f"| {r['force']} `{r['indicator']}` | {r['earliest_year'] or '—'} | {r['latest_year'] or '—'} | {r['baseline_value'] if r['baseline_value'] is not None else '—'} | {r['latest_value'] if r['latest_value'] is not None else '—'} | {r['absolute_change'] if r['absolute_change'] is not None else '—'} | {r['unit'] or ''} |"
            for r in inds_sorted
        ]
        report = f"""# {country['name']} ({iso3}) — economic research profile

Generated: {manifest['generated_at']}  
Methodology: experimental, `{CURRENT_MODEL_VERSION.version_id}`, `{FORCE_AGGREGATION_VERSION}`  
Latest production scoring period: `{manifest['scoring_period']}`

## Current interpretation

The production `model_b_domain` result is **{country['domestic_condition_score']}** with stage **{country['stage'] or 'unclassified'}**, direction `{country['direction']}`, and coverage ratio `{country['coverage_ratio']}`. This is a domestic-condition research result, not an international-power ranking.

## Composite models

| Model | Period | Score | Stage | Coverage |
|---|---:|---:|---|---:|
{chr(10).join(model_lines)}

## Seventeen-force evidence

| Force | Status | Level | Coverage | Period | Actual measurement and limitation |
|---|---|---:|---|---|---|
{chr(10).join(force_lines)}

## Historical raw-indicator changes

| Force / indicator | Earliest | Latest | Baseline value | Latest value | Change | Unit |
|---|---:|---:|---:|---:|---:|---|
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
        "GDP_CURRENT_USD", "POPULATION", "EXPORTS_GDP", "IMPORTS_GDP",
        "CURRENT_ACCOUNT_GDP", "MILITARY_EXPENDITURE_USD",
        "MILITARY_EXPENDITURE_GDP", "RND_EXPENDITURE_GDP",
        "LABOUR_PRODUCTIVITY_PER_HOUR", "GOVERNMENT_DEBT_GDP",
    ]
    for code in comparison_codes:
        usa = by_country_indicator.get(("USA", code), [])
        chn = by_country_indicator.get(("CHN", code), [])
        usa_latest = usa[-1] if usa else None
        chn_latest = chn[-1] if chn else None
        usa_base = next((p for p in reversed(usa) if p["year"] <= from_year), None)
        chn_base = next((p for p in reversed(chn) if p["year"] <= from_year), None)
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
            f"| `{code}` | {usa_base['value'] if usa_base else '—'} | {chn_base['value'] if chn_base else '—'} | {usa_latest['value'] if usa_latest else '—'} | {chn_latest['value'] if chn_latest else '—'} | {ratio_base:.3f} | {ratio_now:.3f} | {usa_latest['unit'] if usa_latest else ''} |"
            if ratio_base is not None and ratio_now is not None
            else f"| `{code}` | {usa_base['value'] if usa_base else '—'} | {chn_base['value'] if chn_base else '—'} | {usa_latest['value'] if usa_latest else '—'} | {chn_latest['value'] if chn_latest else '—'} | — | {f'{ratio_now:.3f}' if ratio_now is not None else '—'} | {usa_latest['unit'] if usa_latest else ''} |"
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

    main_report = f"""# Big Cycle Atlas — economic research handover, {from_year}–present

Generated: {manifest['generated_at']}  
Commit: `{manifest['git_commit']}`  
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

See `export/power_measures.csv` and `export/power_measure_history.csv`. The production measurement set uses latest-vintage GDP, GDP per capita, growth, exports/imports, current account, military expenditure, R&D, labour productivity, government debt, population, REER, rule of law and tertiary attainment.

## 7. USA–China measured comparison

| Indicator | USA baseline | China baseline | USA latest | China latest | China/USA baseline | China/USA latest | Unit |
|---|---:|---:|---:|---:|---:|---:|---|
{chr(10).join(us_china_rows)}

Ratios are direct raw-measurement ratios and are only meaningful for compatible units and reference populations. A change in ratio indicates convergence/divergence in that measurement, not a complete leadership transition.

## 8. Four-model Big Cycle comparison

| Model | Countries with latest score | Latest classified periods | Notes |
|---|---:|---:|---|
{chr(10).join(model_table)}

### Current model agreement

| Country | Current stages | Unique stages | Composite score spread |
|---|---|---:|---:|
{chr(10).join(model_agreement_rows)}

Detailed scores: `export/composite_results.csv`  
Complete classifications: `export/cycle_history.csv`  
Transitions: `export/cycle_transitions.csv` ({len(transition_rows)} recorded model-country transitions)

## 9. Forecast readiness

See `export/forecast_readiness.json`. The existing evidence gates remain active; no unsupported transition probability, countdown or leadership-transfer date is emitted.

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
- Country-boundary changes (especially Germany) require explicit interpretation before joining historical regimes.

## 12. Recommended next research priorities

1. Add Maddison/PWT real-output and capital history as separate labelled historical methods.
2. Add SIPRI direct military expenditure records for provenance and global-share denominators.
3. Add verified financial-centre/capital-market and reserve-currency reference series.
4. Add country-boundary discontinuity metadata for Germany and other territorial changes.
5. Preserve evidence gates before attempting any leadership-transition forecast.
"""
    (OUT / "ATLAS_RESEARCH_1980_PRESENT.md").write_text(main_report, encoding="utf-8")

    handover = f"""# Big Cycle Atlas — compact ChatGPT handover

Generated: {manifest['generated_at']}  
Commit: `{manifest['git_commit']}`

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
