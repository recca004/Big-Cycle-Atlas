"""Regenerate .dev/FORCE_DEPENDENCY_MAP.json from the live backend registries.

Mission 2 (§3): the committed map is DERIVED metadata — it must be
reproducible, and a test fails when it drifts from the registries.

    uv run python scripts/generate_dependency_map.py            # write file
    uv run python scripts/generate_dependency_map.py --check    # exit 1 on drift
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
from app.cycle.reference_universes import REFERENCE_UNIVERSES

OUT_PATH = (
    Path(__file__).resolve().parents[3] / ".dev" / "FORCE_DEPENDENCY_MAP.json"
)


def build_map() -> dict:
    forces = []
    for force_def in FORCE_DEFINITIONS:
        spec = FORCE_AGGREGATION_CONFIGS.get(force_def.code)
        components = []
        if spec is not None:
            for comp in spec.components:
                reg = NORMALIZATION_REGISTRY.get(comp.indicator_code)
                components.append(
                    {
                        "indicator": comp.indicator_code,
                        "role": comp.role.value,
                        "level_family": reg.level_family.value if reg else None,
                        "executable": (
                            reg is not None
                            and comp.role.value in ("core_condition", "proxy_condition", "penalty")
                        ),
                    }
                )
        forces.append(
            {
                "force": force_def.code,
                "live_inputs": list(force_def.live_indicator_codes),
                "ceiling": (
                    force_def.coverage_ceiling.value
                    if force_def.coverage_ceiling
                    else None
                ),
                "level_mode": spec.level_mode.value if spec else None,
                "relative_mode": spec.relative_mode.value if spec else None,
                "momentum_mode": spec.momentum_mode.value if spec else None,
                "components": components,
            }
        )

    # Shared indicators: a live indicator serving more than one force.
    usage: dict[str, list[str]] = {}
    for force_def in FORCE_DEFINITIONS:
        for code in force_def.live_indicator_codes:
            usage.setdefault(code, []).append(force_def.code)
    shared = {k: v for k, v in usage.items() if len(v) > 1}

    return {
        "generated_for": "big-cycle-atlas",
        "model_versions": {
            "normalization": CURRENT_MODEL_VERSION.version_id,
            "force_aggregation": FORCE_AGGREGATION_VERSION,
        },
        "forces": forces,
        "shared_indicators": shared,
        "reference_universes": {
            code: {
                "indicator": u.indicator_code,
                "members": len(u.expected_member_iso3) or None,
                "source": u.source_key,
                "external_code": u.external_code,
            }
            for code, u in REFERENCE_UNIVERSES.items()
        },
        "overlap_notes": [
            "WGI governance cluster (RL/CC/GE/PS) share provider methodology — "
            "correlated perception composites; leadership overlaps "
            "rule_of_law/corruption conceptually (DEC-041 caveat).",
            "LABOUR_FORCE_PARTICIPATION_RATE (character_determination proxy) "
            "overlaps education/human-capital concepts; it is a participation "
            "percentile, never a character score.",
            "MILITARY_EXPENDITURE_USD relative_share uses tracked_8 universe — "
            "a defence-input share, not capability.",
            "EXPORTS_GDP/IMPORTS_GDP/CURRENT_ACCOUNT_GDP/FDI_NET_INFLOWS_GDP "
            "serve trade_capital_flows AND conceptually overlap global_openness "
            "(DEC-035) — flag before any composite weighting.",
            "GROSS_CAPITAL_FORMATION_GDP is context for infrastructure AND "
            "resource_allocation — double-counting risk flagged for composite "
            "work.",
            "GOVERNMENT_DEBT_GDP context overlaps indebtedness concept with "
            "resource allocation.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if committed file differs from regenerated map")
    args = parser.parse_args()
    generated = build_map()
    serialized = json.dumps(generated, indent=2, sort_keys=False) + "\n"
    if args.check:
        current = OUT_PATH.read_text(encoding="utf-8") if OUT_PATH.exists() else ""
        if current != serialized:
            print("DRIFT: FORCE_DEPENDENCY_MAP.json != live registries — "
                  "run scripts/generate_dependency_map.py")
            return 1
        print("OK: dependency map matches live registries")
        return 0
    OUT_PATH.write_text(serialized, encoding="utf-8")
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
