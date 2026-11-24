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
