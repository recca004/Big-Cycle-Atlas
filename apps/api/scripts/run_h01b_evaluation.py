"""Run/persist the H01B (private credit) and H01T (threshold) evaluations.

Both are retrospective diagnostics on the already-inspected 1990-2020 JST R6
holdout, so this script persists append-only EvaluationResult rows ONLY — no
new prediction-ledger entries (the sample produced no new information cutoff).
"""
import asyncio
import sys
from datetime import datetime, timezone

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.path.insert(0, ".")

from sqlalchemy import select

from app.db.session import get_sessionmaker
from app.models import EvaluationResult
from app.research.h01b import evaluate_h01b, evaluate_threshold_heterogeneity
from app.research.scientific_registry import canonical_checksum


async def _persist(session, report: dict, eval_key: str, now: datetime) -> bool:
    exists = (await session.execute(
        select(EvaluationResult.id).where(EvaluationResult.evaluation_key == eval_key)
    )).first()
    if exists:
        return False
    payload = {k: v for k, v in report.items() if k != "generated_at"}
    session.add(EvaluationResult(
        evaluation_key=eval_key,
        hypothesis_code=report["hypothesis_code"],
        protocol_version=report["protocol_version"],
        model_id=report["model_id"], model_version=report["model_version"],
        evaluation_type=report["evaluation_type"],
        result_state=report.get("result_state", "diagnostic"),
        sample_counts=report.get("sample_counts") or {},
        metrics=payload,
        evidence_cutoff=None,
        execution_mode="retrospective_latest_vintage",
        dataset_versions=report.get("dataset_versions") or {"jst_macrohistory": "R6"},
        limitations={"items": report.get("limitations") or [report.get("holdout_integrity", "")]},
        started_at=now, completed_at=now,
        content_checksum=canonical_checksum(payload),
    ))
    return True


async def main() -> None:
    session = get_sessionmaker()()
    now = datetime.now(timezone.utc)
    async with session.begin():
        h01b = await evaluate_h01b(session)
        h01t = await evaluate_threshold_heterogeneity(session)
        ins_b = await _persist(
            session, h01b,
            "H01B-P1.0:retrospective_clustered_diagnostic:1990:jst-r6:v1", now,
        )
        ins_t = await _persist(
            session, h01t,
            "H01T-P1.0:retrospective_threshold_diagnostic:1990:jst-r6:v1", now,
        )
    primary = h01b["predictors"]["private_credit_gdp_5y_change"]["horizons"]["1"]["metrics"]
    print({
        "h01b_inserted": ins_b, "h01t_inserted": ins_t,
        "primary_1y_auc": primary["roc_auc"], "primary_ci": (primary["auc_ci_low"], primary["auc_ci_high"]),
        "episodes": h01b["sample_counts"]["episodes"],
        "result_state": h01b["result_state"],
    })


if __name__ == "__main__":
    asyncio.run(main())
