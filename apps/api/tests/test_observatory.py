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

    async def test_model_comparison_reports_actual_markers_and_equivalence(
        self, client, monkeypatch
    ):
        from app.api.routes import observatory as route_module

        async def fake_core(session, model_id, start_year=1980):
            return {
                "available_periods": ["2025-Q4"],
                "countries": [
                    {
                        "iso3": "USA", "name": "United States",
                        "coverage_ratio": 1.0,
                        "history": [
                            {
                                "period": "2025-Q4", "stage": "Rise",
                                "score": 50.0 + (0.0 if model_id == "model_b_domain" else 1e-14),
                                "momentum": 0.1,
                            }
                        ],
                    }
                ],
            }

        monkeypatch.setattr(
            route_module.observatory_service,
            "compute_core_observatory",
            fake_core,
        )

        r = await client.get("/api/observatory/model-comparison")
        assert r.status_code == 200
        body = r.json()
        assert body["cycle_label"] == "experimental_domestic_condition_cycle"
        assert body["countries"][0]["models"]["model_b_domain"]["stage"] == "Rise"
        assert body["equivalence"]["model_b_domain__model_c_overlap"]["equivalent_under_current_data"] is True
        assert body["equivalence"]["model_b_domain__model_c_overlap"]["independent_evidence"] is False
        assert body["equivalence"]["model_a_equal__model_b_domain"]["independent_evidence"] is False
        assert body["equivalence"]["model_a_equal__model_b_domain"]["shared_input_datasets"] is True
        assert body["equivalence"]["model_a_equal__model_b_domain"]["distinct_weighting_method"] is True


# --- v1.1 refinement regressions ---------------------------------------------

def test_comparison_semantics_own_history_vs_comparable():
    """Regression: Compare displayed USA 97.7 vs CHN 0.5 as a 97.2 cross-country
    difference — but indebtedness is an OWN-HISTORY stress position; the
    spread is meaningless. Levels built from own-history components must be
    marked non-comparable across countries."""
    from app.api.routes.countries import _comparison_semantics

    assert _comparison_semantics("indebtedness", 50.0) == "own_history"
    assert _comparison_semantics("rule_of_law", 50.0) == "comparable"
    assert _comparison_semantics("education", 50.0) == "comparable"
    assert _comparison_semantics("military_strength", None) == "not_scored"
    assert _comparison_semantics("nonexistent_force", 1.0) == "not_scored"


def test_versions_endpoint_is_live_not_hardcoded():
    """Regression: the workspace displayed normalization-v0.8 /
    force-aggregation-v0.3 while the engine had moved on. The versions
    endpoint must reflect the CURRENT registry constants."""
    import asyncio

    from app.api.routes.research import research_versions
    from app.cycle.force_aggregation_definitions import FORCE_AGGREGATION_VERSION
    from app.cycle.normalization_definitions import CURRENT_MODEL_VERSION

    payload = asyncio.run(research_versions())
    assert payload["normalization_version"] == CURRENT_MODEL_VERSION.version_id
    assert payload["force_aggregation_version"] == FORCE_AGGREGATION_VERSION
    assert payload["normalization_version"] != "normalization-v0.8"
    assert payload["force_aggregation_version"] != "force-aggregation-v0.3"
