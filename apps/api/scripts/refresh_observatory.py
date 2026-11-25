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
    args = parser.parse_args()

    collection_summary = None
    if args.collection_summary:
        collection_summary = json.loads(
            args.collection_summary.read_text(encoding="utf-8")
        )

    sm = get_sessionmaker()
    async with sm() as session:
        state = await run_daily_refresh_workflow(
            session,
            model_id=args.model,
            collect_providers=args.collect,
            sources=args.source,
            collection_summary=collection_summary,
        )

    print(
        f"Observatory refresh status={state['status']} | "
        f"new={state['new_observations_count']} | "
        f"revisions={state['revisions_count']} | "
        f"stage_changes={state['changed_classifications_count']} | "
        f"changes={len(state['changes'])}"
    )
    print(state["summary_message"])
    if state["status"] == "update_failed":
        return 1
    if state["status"] == "partial_provider_failure":
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
