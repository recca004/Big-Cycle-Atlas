"""Run/persist the H01 retrospective evaluation and append-only predictions."""
import asyncio
import sys
from datetime import datetime, timezone

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.path.insert(0, ".")

from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models import EvaluationResult, PredictionLedgerEntry, PredictionOutcome
from app.research.h01 import (
    _percentile_scores, build_samples, evaluate_h01, load_jst_panel,
)
from app.research.scientific_registry import canonical_checksum


async def main() -> None:
    session = get_sessionmaker()()
    now = datetime.now(timezone.utc)
    async with session.begin():
        report = await evaluate_h01(session)
        panel, coverage, events = await load_jst_panel(session)
        existing_evals = {
            r.evaluation_key
            for r in (await session.execute(select(EvaluationResult.evaluation_key))).all()
        }
        eval_key = "H01-P1.0:retrospective_chronological_holdout:1990:jst-r6:v2"
        inserted_eval = 0
        payload = {k: v for k, v in report.items() if k != "generated_at"}
        if eval_key not in existing_evals:
            session.add(EvaluationResult(
                evaluation_key=eval_key,
                hypothesis_code="H01", protocol_version="H01-P1.0",
                model_id=report["model_id"], model_version=report["model_version"],
                evaluation_type=report["evaluation_type"],
                result_state=report["result_state"],
                sample_counts=report["sample_counts"] | {"horizons": report["horizons"]},
                metrics={"horizons": report["horizons"]},
                evidence_cutoff=None,
                execution_mode="retrospective_latest_vintage",
                dataset_versions=report["dataset_versions"],
                limitations={"items": report["limitations"]},
                started_at=now, completed_at=now,
                content_checksum=canonical_checksum(payload),
            ))
            inserted_eval += 1

        existing_preds = {
            r.prediction_key
            for r in (await session.execute(select(PredictionLedgerEntry.prediction_key))).all()
        }
        existing_prediction_ids = {}
        inserted_predictions = inserted_outcomes = 0
        for horizon in (1, 2, 5):
            samples = build_samples(panel, coverage, events, horizon)
            train_values = [s.predictor for s in samples if s.outcome_year < 1990]
            test = [s for s in samples if s.outcome_year >= 1990]
            for score, sample in zip(_percentile_scores(train_values, [s.predictor for s in test]), test):
                key = f"H01-P1.0:debtgdp_5y_change_univariate:{sample.entity_code}:{sample.forecast_origin_year}:{horizon}y"
                if key in existing_preds:
                    continue
                content = {
                    "score_percentile": score, "predictor": sample.predictor,
                    "outcome_year": sample.outcome_year,
                }
                origin = datetime(sample.forecast_origin_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
                prediction = PredictionLedgerEntry(
                    prediction_key=key, hypothesis_code="H01", protocol_version="H01-P1.0",
                    model_id="debtgdp_5y_change_univariate", model_version="v1",
                    entity_code=sample.entity_code, entity_type="country",
                    forecast_origin=origin, info_cutoff=origin,
                    horizon_start=datetime(sample.outcome_year, 1, 1, tzinfo=timezone.utc),
                    horizon_end=datetime(sample.outcome_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                    target_outcome="banking_crisis_onset",
                    prediction_status="available",
                    prediction_payload={"risk_score_percentile": score, "predictor_debtgdp_5y_change": sample.predictor},
                    uncertainty_payload=None,
                    data_coverage={"retrospective_only": True, "release_safe": False},
                    input_vintage_ids={"source": "jst_macrohistory", "dataset_version": "R6"},
                    dataset_versions={"jst_macrohistory": "R6"},
                    evaluation_status="evaluated",
                    recorded_at=now, content_checksum=canonical_checksum(content),
                )
                session.add(prediction)
                existing_preds.add(key)
                await session.flush()
                outcome_payload = {"outcome_year": sample.outcome_year, "banking_crisis_onset": sample.outcome}
                session.add(PredictionOutcome(
                    prediction_id=prediction.id, outcome_source_key="jst_macrohistory",
                    outcome_status="realized_positive" if sample.outcome else "realized_negative",
                    outcome_payload=outcome_payload,
                    observed_at=datetime(sample.outcome_year, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                    recorded_at=now, outcome_checksum=canonical_checksum(outcome_payload),
                ))
                inserted_predictions += 1; inserted_outcomes += 1
    print({"evaluation_inserted": inserted_eval, "predictions_inserted": inserted_predictions, "outcomes_inserted": inserted_outcomes, "result_state": report["result_state"], "horizons": report["horizons"]})


if __name__ == "__main__":
    asyncio.run(main())
