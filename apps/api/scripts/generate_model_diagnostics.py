"""Systematic retrospective model diagnostics (Mission 4 §26).

Runs every experimental composite model across every tracked country at
annual (Q4) scoring snapshots and writes a reproducible manifest to
.dev/MODEL_DIAGNOSTICS.json.

Everything produced here is RETROSPECTIVE (latest stored vintages,
execution_mode=retrospective_latest_vintage, backtest_safe=False) — the
manifest is a model-behaviour diagnostic, never a backtest.

Run:  python scripts/generate_model_diagnostics.py [--start 2000]
"""
from __future__ import annotations

import asyncio
import json
import math
import statistics
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.cycle.normalization_definitions import (  # noqa: E402
    CURRENT_MODEL_VERSION,
    ScoringPeriod,
)
from app.db.session import get_sessionmaker  # noqa: E402
from app.models import Country  # noqa: E402
from app.research.composite import COMPOSITE_MODELS  # noqa: E402
from app.research import service as research_service  # noqa: E402
from sqlalchemy import select  # noqa: E402

OUT = (
    Path(__file__).resolve().parents[3] / ".dev" / "MODEL_DIAGNOSTICS.json"
)


def _latest_completed() -> ScoringPeriod:
    today = datetime.now(timezone.utc).date()
    quarter = (today.month - 1) // 3
    if quarter == 0:
        return ScoringPeriod(today.year - 1, 4)
    return ScoringPeriod(today.year, quarter - 1)


@dataclass
class PeriodRecord:
    period: str
    score: float | None
    coverage: float
    included: tuple[str, ...]
    missing: tuple[str, ...]
    stage: str | None = None
    phase: str | None = None


async def _country_iso3s(session) -> list[str]:
    rows = (await session.execute(select(Country.iso3).order_by(Country.iso3))).all()
    return [r[0] for r in rows]


async def run(start_year: int) -> dict:
    latest = _latest_completed()
    end_year = latest.year
    sessionmaker = get_sessionmaker()

    manifest: dict = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "normalization_version": CURRENT_MODEL_VERSION.version_id,
        "execution_mode": "retrospective_latest_vintage",
        "retrospective": True,
        "backtest_safe": False,
        "period_range": [f"{start_year}-Q4", f"{end_year}-Q4"],
        "methodology_status": "experimental",
        "models": {},
        "countries_evaluated": [],
        "disclaimer": (
            "Retrospective latest-vintage diagnostics — later revisions are "
            "visible in earlier periods' inputs. NOT a backtest; the "
            "strict_as_of mode currently cannot produce scores because no "
            "provider release evidence is ingested (§21)."
        ),
    }

    async with sessionmaker() as session:
        countries = await _country_iso3s(session)
    manifest["countries_evaluated"] = countries

    # scores[model][iso3][period] -> CompositeResult
    for model_id in sorted(COMPOSITE_MODELS):
        model = COMPOSITE_MODELS[model_id]
        model_block: dict = {
            "model_id": model_id,
            "model_version": model.version,
            "kind": model.kind,
            "countries": {},
            "aggregate": {},
        }
        for iso3 in countries:
            records: list[PeriodRecord] = []
            for year in range(start_year, end_year + 1):
                sp = ScoringPeriod(year, 4)
                if (sp.year, sp.quarter) > (latest.year, latest.quarter):
                    break
                async with sessionmaker() as session:
                    result = await research_service.composite_at(
                        session, iso3, sp, model_id
                    )
                records.append(
                    PeriodRecord(
                        period=f"{year}-Q4",
                        score=result.score,
                        coverage=result.coverage_ratio,
                        included=result.included_forces,
                        missing=result.missing_forces,
                    )
                )
            # cycle classification over the same retrospective series
            async with sessionmaker() as session:
                cycle = await research_service.cycle_history(
                    session, iso3, model_id, start_year, end_year, latest
                )
            stage_by_period = {p.period: p for p in cycle.points}
            for rec in records:
                cp = stage_by_period.get(rec.period)
                if cp is not None:
                    rec.stage = cp.stage.value if cp.stage else None
                    rec.phase = cp.phase.value if cp.phase else None

            scored = [r.score for r in records if r.score is not None]
            included_union = sorted(
                {f for r in records for f in r.included}
            )
            excluded_union = sorted(
                {f for r in records for f in r.missing}
            )
            stage_seq = [r.stage for r in records if r.stage]
            model_block["countries"][iso3] = {
                "earliest_usable_period": next(
                    (r.period for r in records if r.score is not None), None
                ),
                "valid_periods": len(scored),
                "unavailable_periods": len(records) - len(scored),
                "included_forces": included_union,
                "missing_forces": excluded_union,
                "mean_coverage": (
                    statistics.mean(r.coverage for r in records)
                    if records else None
                ),
                "score_mean": (
                    statistics.mean(scored) if scored else None
                ),
                "score_volatility": (
                    statistics.pstdev(scored) if len(scored) > 1 else None
                ),
                "stage_transitions": len(cycle.transitions),
                "stages_seen": sorted(set(stage_seq)),
                "transitions_detail": list(cycle.transitions),
                "coverage_ratio_path": cycle.coverage_ratio,
                "points": [
                    {
                        "period": r.period,
                        "score": r.score,
                        "coverage": r.coverage,
                        "included": list(r.included),
                        "missing": list(r.missing),
                        "stage": r.stage,
                        "phase": r.phase,
                    }
                    for r in records
                ],
            }
        manifest["models"][model_id] = model_block

    # Model disagreement: per country per period, spread across models
    disagreement: dict[str, list[dict]] = {c: [] for c in countries}
    for iso3 in countries:
        periods = set()
        for m in manifest["models"].values():
            periods.update(
                p["period"] for p in m["countries"][iso3]["points"]
            )
        for period in sorted(periods):
            vals = [
                p["score"]
                for m in manifest["models"].values()
                for p in m["countries"][iso3]["points"]
                if p["period"] == period and p["score"] is not None
            ]
            if len(vals) >= 2:
                disagreement[iso3].append(
                    {
                        "period": period,
                        "models_scored": len(vals),
                        "min": min(vals),
                        "max": max(vals),
                        "spread": max(vals) - min(vals),
                    }
                )
    manifest["model_disagreement"] = {
        iso3: {
            "periods_compared": len(entries),
            "mean_spread": (
                statistics.mean(e["spread"] for e in entries)
                if entries else None
            ),
            "max_spread": (
                max(e["spread"] for e in entries) if entries else None
            ),
            "entries": entries,
        }
        for iso3, entries in disagreement.items()
    }
    return manifest


def main() -> None:
    start = 2000
    if "--start" in sys.argv:
        start = int(sys.argv[sys.argv.index("--start") + 1])
    manifest = asyncio.run(run(start))
    OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    total = sum(
        c["valid_periods"]
        for m in manifest["models"].values()
        for c in m["countries"].values()
    )
    print(
        f"wrote {OUT} — {len(manifest['models'])} models x "
        f"{len(manifest['countries_evaluated'])} countries, "
        f"{total} valid composite periods"
    )


if __name__ == "__main__":
    main()
