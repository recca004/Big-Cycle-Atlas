"""Daily Big Cycle Observatory refresh workflow (§9).

Reuses the existing ingestion adapters & immutable-vintage persistence
(`collect_provider_observations` / `run_ingestion`), recalculates all
force measurements and experimental cycle positions, compares against
the previous successful snapshot, records genuine changes, and updates
the homepage observatory cache.

Usage:
    python scripts/refresh_observatory.py                  # recalculate + snapshot diff
    python scripts/refresh_observatory.py --collect        # collect providers + recalculate + diff
    python scripts/refresh_observatory.py --collect --source world_bank
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import get_sessionmaker  # noqa: E402
from app.research.composite import COMPOSITE_MODELS  # noqa: E402
from app.research.observatory import run_daily_refresh_workflow  # noqa: E402


async def main() -> int:
    parser = argparse.ArgumentParser(description="Daily Big Cycle Observatory refresh")
    parser.add_argument(
        "--collect",
        action="store_true",
        help="Run provider data collection before recalculating",
    )
    parser.add_argument(
        "--source",
        action="append",
        default=None,
        help="Optional provider key(s) to collect (world_bank, bis, oecd, imf_weo)",
    )
    parser.add_argument(
        "--model",
        default="model_b_domain",
        help="Experimental composite model id",
    )
    parser.add_argument(
        "--collection-summary",
        type=Path,
        default=None,
        help="JSON summary produced by collect_snapshot.py --summary-json",
    )
    parser.add_argument(
        "--all-models",
        action="store_true",
        help="Recalculate every experimental composite model; --model remains the reported default",
    )
    args = parser.parse_args()

    collection_summary = None
    if args.collection_summary:
        collection_summary = json.loads(
            args.collection_summary.read_text(encoding="utf-8")
        )

    model_ids = [args.model]
    if args.all_models:
        model_ids = [args.model] + [
            model_id for model_id in COMPOSITE_MODELS if model_id != args.model
        ]

    sm = get_sessionmaker()
    states = []
    async with sm() as session:
        for index, model_id in enumerate(model_ids):
            reported_model = index == 0
            state = await run_daily_refresh_workflow(
                session,
                model_id=model_id,
                collect_providers=args.collect and reported_model,
                sources=args.source if reported_model else None,
                collection_summary=(
                    collection_summary if reported_model else None
                ),
                persist_result=reported_model,
            )
            states.append(state)
            print(
                f"Observatory refresh model={model_id} status={state['status']} | "
                f"new={state['new_observations_count']} | "
                f"revisions={state['revisions_count']} | "
                f"stage_changes={state['changed_classifications_count']} | "
                f"changes={len(state['changes'])}"
            )
            print(state["summary_message"])

    state = states[0]
    if any(s["status"] == "update_failed" for s in states):
        return 1
    if any(s["status"] == "partial_provider_failure" for s in states):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
