"""Observatory unit + route tests — snapshot diffing honesty and the
lightweight endpoints that don't require computed composites."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.research.observatory import (
    diff_snapshots,
    get_refresh_job_status,
    to_utc_iso,
    to_zurich_display,
)


def _country(stage, score=60.0, momentum=0.5):
    return {
        "name": "Testland",
        "stage": stage,
        "phase": stage,
        "domestic_condition_score": score,
        "momentum": momentum,
        "coverage_ratio": 0.8,
        "period": "2025-Q4",
        "forces": {},
        "power": {},
    }


def _snap(stage="RISE", **kw):
    return {
        "calculated_at": "2026-01-01T00:00:00Z",
        "db_fingerprint": "fp",
        "model_id": "model_b_domain",
        "scoring_period": "2025-Q4",
        "countries": {"USA": _country(stage, **kw)},
    }


class TestTimeHelpers:
    def test_to_utc_iso(self):
        dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert to_utc_iso(dt).startswith("2026-01-01T12:00")
        assert to_utc_iso(None) is None

    def test_to_zurich_display(self):
        dt = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        out = to_zurich_display(dt)
        assert out is not None and "2026-01-01" in out
        assert to_zurich_display(None) is None


class TestDiffSnapshots:
    def test_first_snapshot_reports_no_changes(self):
        out = diff_snapshots(None, _snap())
        assert out["changed_classifications_count"] == 0
        assert out["changes"] == []
        assert "No new economic changes" in out["summary_message"]

    def test_identical_snapshots_report_no_changes(self):
        out = diff_snapshots(_snap(), _snap())
        assert out["changed_classifications_count"] == 0
        assert out["changes"] == []

    def test_genuine_stage_change_is_recorded(self):
        out = diff_snapshots(_snap("RISE"), _snap("DECLINE"))
        assert out["changed_classifications_count"] == 1
        ch = out["changes"][0]
        assert ch["category"] == "classification"
        assert ch["previous_value"] == "RISE"
        assert ch["current_value"] == "DECLINE"
        assert ch["difference"] == "RISE -> DECLINE"

    def test_missing_stage_is_not_deterioration(self):
        # Current value None (data dropped) must NOT become a decline record.
        out = diff_snapshots(_snap("RISE"), _snap(None))
        class_changes = [
            c for c in out["changes"] if c["category"] == "classification"
        ]
        assert class_changes == []

    def test_newly_classifiable_is_coverage_not_regression(self):
        out = diff_snapshots(_snap(None), _snap("RISE"))
        cov = [c for c in out["changes"] if c["category"] == "coverage"]
        assert len(cov) == 1
        assert cov[0]["direction"] == "coverage_added"


class TestRefreshJob:
    def test_initial_job_state_is_idle(self):
        job = get_refresh_job_status()
        assert job["status"] in {"idle", "running", "succeeded", "failed"}
        assert job["running"] is False


@pytest.mark.asyncio
class TestObservatoryRoutes:
    async def test_refresh_status_endpoint(self, client):
        r = await client.get("/api/observatory/refresh/status")
        assert r.status_code == 200
        body = r.json()
        assert "status" in body and "running" in body

    async def test_unknown_model_rejected(self, client):
        r = await client.get(
            "/api/observatory/freshness", params={"model": "bogus"}
        )
        assert r.status_code == 422

    async def test_overview_rejects_unknown_model(self, client):
        r = await client.get(
            "/api/observatory/overview", params={"model": "bogus"}
        )
        assert r.status_code == 422

    async def test_transition_rejects_unknown_model(self, client):
        r = await client.get(
            "/api/observatory/transition", params={"model": "bogus"}
        )
        assert r.status_code == 422
