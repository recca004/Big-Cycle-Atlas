"""Mission 2 (§3): generated metadata must not drift from live registries.

FORCE_DEPENDENCY_MAP.json is DERIVED — a stale commit is a real defect.
"""
import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]


def test_dependency_map_matches_live_registries():
    result = subprocess.run(
        [sys.executable, "scripts/generate_dependency_map.py", "--check"],
        cwd=API_DIR, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_project_metadata_matches_registries():
    """§4/Mission 4: PROJECT_METADATA.json is derived metadata — drift = stale docs."""
    import subprocess, sys
    from pathlib import Path
    repo = Path(__file__).resolve().parents[3]
    r = subprocess.run(
        [sys.executable, "scripts/generate_project_metadata.py", "--check"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, (
        "PROJECT_METADATA.json is stale — run scripts/generate_project_metadata.py\n"
        + r.stdout + r.stderr)


def test_force_matrix_matches_live_registries():
    """§4/Mission 4: FORCE_COMPLETION_MATRIX.md is derived — drift = stale docs."""
    r = subprocess.run(
        [sys.executable, "scripts/generate_force_matrix.py", "--check"],
        cwd=API_DIR, capture_output=True, text=True,
    )
    assert r.returncode == 0, (
        "FORCE_COMPLETION_MATRIX.md is stale — run "
        "scripts/generate_force_matrix.py\n" + r.stdout + r.stderr)


def test_primary_classification_sums_to_17():
    import json
    from pathlib import Path
    meta = json.loads(
        (Path(__file__).resolve().parents[3] / ".dev" / "PROJECT_METADATA.json")
        .read_text())
    fc = meta["forces"]
    assert fc["total"] == 17
    assert sum(fc["primary_counts"].values()) == 17
    assert fc["counts_sum_to_total"] is True
