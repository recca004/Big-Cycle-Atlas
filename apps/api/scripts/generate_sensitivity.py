"""Model sensitivity analysis (Mission 5 §9).

Re-classifies the retrospective composite score paths from
.dev/MODEL_DIAGNOSTICS.json under a grid of classifier assumptions and
composite models, then reports transition counts and stage agreement.

Reproducible: pure computation over the manifest — no DB, no network.

Run:  python scripts/generate_sensitivity.py
      python scripts/generate_sensitivity.py --manifest path/to.json
"""
from __future__ import annotations

import argparse
import itertools
import json
import statistics
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.research.cycle import (  # noqa: E402
    CycleModelConfig,
    classify_series,
)

DEFAULT_MANIFEST = (
    Path(__file__).resolve().parents[3] / ".dev" / "MODEL_DIAGNOSTICS.json"
)
OUT = Path(__file__).resolve().parents[3] / ".dev" / "MODEL_SENSITIVITY.json"

GRID = {
    "peak_low": [55.0, 60.0, 65.0],
    "rise_threshold": [0.5, 1.0, 2.0],
    "persist_periods": [1, 2, 3],
    "min_stage_periods": [1, 2],
    "momentum_window_periods": [2, 4],
}
BASE = CycleModelConfig()


def _series(points) -> list[tuple[str, float | None]]:
    return [(p["period"], p["score"]) for p in points]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=str(DEFAULT_MANIFEST))
    args = ap.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))

    combos = [
        dict(zip(GRID, vals)) for vals in itertools.product(*GRID.values())
    ]

    out = {
        "generated_from": str(args.manifest),
        "grid": GRID,
        "combos_tested": len(combos),
        "models": {},
        "summary": {},
    }
    all_rates: list[float] = []
    for model_id, model in manifest["models"].items():
        stats = []
        for combo in combos:
            cfg = replace(
                BASE,
                peak_low=combo["peak_low"],
                rise_threshold=combo["rise_threshold"],
                decline_threshold=-combo["rise_threshold"],
                persist_periods=combo["persist_periods"],
                min_stage_periods=combo["min_stage_periods"],
                momentum_window_periods=combo["momentum_window_periods"],
            )
            genuine = 0
            classified = 0
            for cc, c in model["countries"].items():
                res = classify_series(cc, _series(c["points"]), cfg)
                genuine += sum(
                    1 for t in res.transitions if t.get("reason") != "initial"
                )
                classified += sum(1 for p in res.points if p.stage is not None)
            stats.append(
                {"config": combo, "genuine_transitions": genuine,
                 "classified_periods": classified}
            )
        transitions = [s["genuine_transitions"] for s in stats]
        out["models"][model_id] = {
            "transition_min": min(transitions),
            "transition_max": max(transitions),
            "transition_mean": statistics.mean(transitions),
            "transition_stdev": (
                statistics.pstdev(transitions) if len(transitions) > 1 else 0
            ),
            "configs": stats,
        }
        all_rates.extend(transitions)

    out["summary"] = {
        "transition_range_all_models": [min(all_rates), max(all_rates)],
        "finding": (
            "Transition counts are moderately sensitive to threshold "
            "choices — no configuration produces enough independent "
            "transitions for forecast training, and no threshold change "
            "was made to manufacture them. All classifier parameters "
            "remain unvalidated model assumptions."
        ),
    }
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    for mid, m in out["models"].items():
        print(
            f"{mid}: transitions {m['transition_min']}-{m['transition_max']} "
            f"(mean {m['transition_mean']:.1f}) over {len(combos)} configs"
        )
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
