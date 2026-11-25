"""H01 exploratory debt/crisis evaluation."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_sources.jst_macrohistory import JST_DATASET_VERSION, JST_SOURCE_KEY
from app.models import CrisisCoverage, CrisisEvent, ResearchObservation


@dataclass(frozen=True)
class EvaluationSample:
    entity_code: str
    forecast_origin_year: int
    outcome_year: int
    predictor: float
    outcome: bool


def _auc(samples: list[tuple[float, bool]]) -> float | None:
    positives = [s for s, y in samples if y]
    negatives = [s for s, y in samples if not y]
    if not positives or not negatives:
        return None
    wins = total = 0
    for p in positives:
        for n in negatives:
            wins += p > n or p == n and 0.5
            total += 1
    return wins / total if total else None


def _percentile_scores(train_values: list[float], values: list[float]) -> list[float]:
    ordered = sorted(train_values)
    n = len(ordered)
    return [sum(1 for x in ordered if x <= v) / n if n else 0.0 for v in values]


async def load_jst_panel(session: AsyncSession):
    rows = (await session.execute(select(ResearchObservation).where(
        ResearchObservation.source_key == JST_SOURCE_KEY,
        ResearchObservation.dataset_version == JST_DATASET_VERSION,
    ))).scalars().all()
    panel: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
    for row in rows:
        panel[(row.entity_code, row.period_start.year)][row.variable_code] = row.value
    coverage = {
        (r.entity_code, r.period_start.year)
        for r in (await session.execute(select(CrisisCoverage).where(
            CrisisCoverage.source_key == JST_SOURCE_KEY,
            CrisisCoverage.dataset_version == JST_DATASET_VERSION,
            CrisisCoverage.event_type == "banking_crisis",
        ))).scalars()
    }
    events = {
        (r.entity_code, r.start_period.year)
        for r in (await session.execute(select(CrisisEvent).where(
            CrisisEvent.source_key == JST_SOURCE_KEY,
            CrisisEvent.dataset_version == JST_DATASET_VERSION,
            CrisisEvent.event_type == "banking_crisis",
            CrisisEvent.event_state == "onset",
        ))).scalars()
    }
    return panel, coverage, events


def build_samples(panel, coverage, events, horizon_years: int) -> list[EvaluationSample]:
    samples = []
    for entity, outcome_year in sorted(coverage):
        origin = outcome_year - horizon_years
        before = panel.get((entity, origin - 5), {}).get("debtgdp")
        current = panel.get((entity, origin), {}).get("debtgdp")
        if before is None or current is None:
            continue
        samples.append(EvaluationSample(
            entity_code=entity, forecast_origin_year=origin,
            outcome_year=outcome_year, predictor=current - before,
            outcome=(entity, outcome_year) in events,
        ))
    return samples


async def evaluate_h01(session: AsyncSession, split_year: int = 1990) -> dict:
    panel, coverage, events = await load_jst_panel(session)
    horizons = {}
    for horizon in (1, 2, 5):
        samples = build_samples(panel, coverage, events, horizon)
        train = [s for s in samples if s.outcome_year < split_year]
        test = [s for s in samples if s.outcome_year >= split_year]
        train_values = [s.predictor for s in train]
        scores = _percentile_scores(train_values, [s.predictor for s in test])
        base_rate = sum(s.outcome for s in test) / len(test) if test else None
        threshold = 0.8
        predicted = [score >= threshold for score in scores]
        tp = sum(p and s.outcome for p, s in zip(predicted, test))
        fp = sum(p and not s.outcome for p, s in zip(predicted, test))
        fn = sum((not p) and s.outcome for p, s in zip(predicted, test))
        tn = sum((not p) and not s.outcome for p, s in zip(predicted, test))
        top = [(score, s) for score, s in zip(scores, test) if score >= threshold]
        horizons[str(horizon)] = {
            "samples": len(samples), "train_samples": len(train),
            "test_samples": len(test), "test_events": sum(s.outcome for s in test),
            "base_rate": base_rate,
            "auc": _auc([(score, s.outcome) for score, s in zip(scores, test)]),
            "top_quintile_precision": (sum(s.outcome for _, s in top) / len(top)) if top else None,
            "confusion_at_p80": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
            "predictor": "debtgdp five-year change at forecast origin",
        }
    sufficient = any(
        h["test_events"] >= 10 and h["test_samples"] >= 100
        for h in horizons.values()
    )
    if not sufficient:
        result_state = "insufficient_sample"
    elif all(
        (h["auc"] is not None and h["auc"] <= 0.5)
        or (
            h["top_quintile_precision"] is not None
            and h["base_rate"] is not None
            and h["top_quintile_precision"] <= h["base_rate"]
        )
        for h in horizons.values()
    ):
        result_state = "no_evidence_of_improved_predictive_value"
    else:
        result_state = "exploratory_association"
    return {
        "hypothesis_code": "H01", "protocol_version": "H01-P1.0",
        "model_id": "debtgdp_5y_change_univariate", "model_version": "v1",
        "evaluation_type": "retrospective_chronological_holdout",
        "split_year": split_year, "horizons": horizons,
        "result_state": result_state,
        "limitations": [
            "retrospective JST R6 dataset, not real-time vintages",
            "annual crisis onsets only",
            "correlated international crises are not independent experiments",
            "univariate benchmark only; not a calibrated probability model",
        ],
        "sample_counts": {"coverage_rows": len(coverage), "event_onsets": len(events)},
        "dataset_versions": {"jst_macrohistory": JST_DATASET_VERSION},
        "generated_at": datetime.now(timezone.utc),
    }
