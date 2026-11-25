"""Regenerate .dev/PROJECT_METADATA.json from the live backend registries.

Mission 4 (§4): one reproducible source for force classification counts,
model versions and the methodology inventory — eliminates conflicting
manual counts across docs. A drift test fails when it goes stale.

    .venv/Scripts/python scripts/generate_project_metadata.py           # write
    .venv/Scripts/python scripts/generate_project_metadata.py --check   # drift
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.cycle.force_aggregation_definitions import (
    FORCE_AGGREGATION_CONFIGS,
    FORCE_AGGREGATION_VERSION,
)
from app.cycle.force_definitions import FORCE_DEFINITIONS
from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    NORMALIZATION_REGISTRY,
)
from app.research.methodology_registry import (
    METHODOLOGY_REGISTRY,
    MethodologyState,
    methods_for_force,
)

OUT_PATH = (
    Path(__file__).resolve().parents[3] / ".dev" / "PROJECT_METADATA.json"
)

PRIMARY_CLASSES = (
    "level_published", "dimension_only", "context_profile", "deferred",
)


def _primary(fd, approved) -> str:
    if any(m.dimension == "level" for m in approved):
        return "level_published"
    if approved:
        return "dimension_only"
    if fd.live_indicator_codes or (fd.code == "geography" and
                                   methods_for_force(fd.code)):
        return "context_profile"
    return "deferred"


def build() -> dict:
    counts = {c: 0 for c in PRIMARY_CLASSES}
    forces = []
    for fd in FORCE_DEFINITIONS:
        methods = methods_for_force(fd.code)
        approved = [m for m in methods
                    if m.state is MethodologyState.approved_production]
        primary = _primary(fd, approved)
        counts[primary] += 1
        forces.append({
            "force_code": fd.code,
            "primary_classification": primary,
            "published_dimensions": sorted(
                {m.dimension for m in approved}),
            "coverage_ceiling": (fd.coverage_ceiling.value
                                 if fd.coverage_ceiling else None),
        })
    by_state: dict[str, int] = {}
    for m in METHODOLOGY_REGISTRY.values():
        by_state[m.state.value] = by_state.get(m.state.value, 0) + 1
    return {
        "generated_from": "live backend registries",
        "model_versions": {
            "normalization": CURRENT_MODEL_VERSION.version_id,
            "force_aggregation": FORCE_AGGREGATION_VERSION,
        },
        "forces": {
            "total": len(FORCE_DEFINITIONS),
            "primary_counts": counts,
            "counts_sum_to_total":
                sum(counts.values()) == len(FORCE_DEFINITIONS),
            "list": forces,
        },
        "methodology": {
            "total_methods": len(METHODOLOGY_REGISTRY),
            "by_state": dict(sorted(by_state.items())),
            "method_ids": sorted(METHODOLOGY_REGISTRY),
        },
        "normalization": {
            "registered_indicators": len(NORMALIZATION_REGISTRY),
        },
        "aggregation": {
            "configured_forces": len(FORCE_AGGREGATION_CONFIGS),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 when committed metadata drifts")
    args = ap.parse_args()
    payload = build()
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not OUT_PATH.exists():
            print("missing generated file:", OUT_PATH)
            return 1
        if OUT_PATH.read_text(encoding="utf-8") != text:
            print("STALE: run generate_project_metadata.py")
            return 1
        print("up to date")
        return 0
    OUT_PATH.write_text(text, encoding="utf-8")
    print("wrote", OUT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
