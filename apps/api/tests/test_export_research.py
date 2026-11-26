import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from export_research import _trend


def test_export_trend_does_not_fabricate_missing_baseline():
    trend = _trend(
        [
            {"year": 1975, "value": 10.0},
            {"year": 1978, "value": 11.0},
        ],
        start_year=1980,
    )

    assert trend["baseline_year"] is None
    assert trend["baseline_value"] is None
    assert trend["absolute_change"] is None
    assert trend["percentage_change"] is None
    assert trend["latest_year"] == 1978
    assert trend["latest_value"] == 11.0
    assert trend["full_baseline_year"] == 1975


def test_export_trend_uses_first_selected_range_observation():
    trend = _trend(
        [
            {"year": 1998, "value": 10.0},
            {"year": 2000, "value": 11.0},
        ],
        start_year=1980,
    )

    assert trend["baseline_year"] == 1998
    assert trend["baseline_value"] == 10.0
    assert trend["absolute_change"] == 1.0


def test_export_trend_uses_latest_observation_not_later_than_baseline():
    trend = _trend(
        [
            {"year": 1975, "value": 5.0},
            {"year": 1980, "value": 10.0},
            {"year": 1990, "value": 15.0},
        ],
        start_year=1980,
    )

    assert trend["baseline_year"] == 1980
    assert trend["baseline_value"] == 10.0
    assert trend["absolute_change"] == 5.0
    assert trend["percentage_change"] == 50.0
