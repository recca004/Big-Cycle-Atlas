"""Forecast architecture + readiness gates (Mission 5 §10-§12)."""
from app.research.forecast import (
    ForecastHorizon,
    ReadinessRequirements,
    TransitionRecord,
    evaluate_readiness,
    persistence_benchmark,
    transitions_within,
)


def _t(period: str, model: str = "m") -> TransitionRecord:
    return TransitionRecord(
        country_iso3="USA", period=period,
        from_stage="PEAK", to_stage="EARLY_DECLINE", model_id=model,
    )


def _periods(start: int, n: int) -> list[str]:
    return [f"{start + i}-Q4" for i in range(n)]


def test_transitions_within_horizon():
    ts = [_t("2021-Q1"), _t("2022-Q4"), _t("2025-Q1")]
    assert transitions_within(ts, "2020-Q4", ForecastHorizon.one_year) == 1
    assert transitions_within(ts, "2020-Q4", ForecastHorizon.two_years) == 2
    assert transitions_within(ts, "2020-Q4", ForecastHorizon.five_years) == 3
    # boundaries: origin itself excluded, horizon end included
    assert transitions_within([_t("2020-Q4")], "2020-Q4",
                              ForecastHorizon.one_year) == 0
    assert transitions_within([_t("2021-Q4")], "2020-Q4",
                              ForecastHorizon.one_year) == 1
    assert transitions_within([_t("2022-Q1")], "2020-Q4",
                              ForecastHorizon.one_year) == 0


def test_readiness_all_gates_pass():
    req = ReadinessRequirements(
        min_total_scored_periods=10,
        min_independent_transitions=5,
        min_strict_eligible_periods=1,
        min_oos_periods=3,
    )
    periods = _periods(2000, 26)
    ts = [_t(p) for p in periods[2:20:3]]  # 6 genuine transitions
    report = evaluate_readiness("m", "v1", periods, ts, strict_eligible_periods=50,
                                requirements=req)
    assert report.overall_available is True
    assert all(hr.available for hr in report.horizon_results)


def test_readiness_fails_without_transitions():
    req = ReadinessRequirements(min_total_scored_periods=5,
                                min_independent_transitions=3,
                                min_strict_eligible_periods=1,
                                min_oos_periods=2)
    periods = _periods(2000, 20)
    report = evaluate_readiness("m", "v1", periods, [], 100, requirements=req)
    assert report.overall_available is False
    assert "independent_transitions" in report.blockers
    for hr in report.horizon_results:
        assert hr.available is False
        assert hr.unavailable_reason  # always explains itself


def test_readiness_fails_without_strict_evidence():
    req = ReadinessRequirements(min_total_scored_periods=5,
                                min_independent_transitions=1,
                                min_strict_eligible_periods=1,
                                min_oos_periods=2)
    periods = _periods(2000, 20)
    ts = [_t(p) for p in periods[2:12]]
    report = evaluate_readiness("m", "v1", periods, ts, 0, requirements=req)
    assert "strict_availability" in report.blockers


def test_long_horizon_shrinks_eligible_origins():
    req = ReadinessRequirements(min_total_scored_periods=5,
                                min_independent_transitions=1,
                                min_strict_eligible_periods=1,
                                min_oos_periods=2)
    periods = _periods(2000, 12)
    report = evaluate_readiness("m", "v1", periods, [_t("2005-Q4")], 5,
                                requirements=req)
    by_hz = {h.horizon: h for h in report.horizon_results}
    # longer horizons shrink the eligible-origin window
    assert (
        by_hz[ForecastHorizon.ten_years].eligible_samples
        < by_hz[ForecastHorizon.one_year].eligible_samples
    )
    # 10y needs 40 forward quarters: only the first 2 annual origins qualify
    assert by_hz[ForecastHorizon.ten_years].eligible_samples == 2


def test_persistence_benchmark():
    res = persistence_benchmark(["PEAK", "PEAK", "DECLINE", "DECLINE", None])
    assert res["samples"] == 3  # the (DECLINE, None) pair is dropped
    assert res["correct"] == 2
    assert res["accuracy"] == 2 / 3
    assert persistence_benchmark([])["accuracy"] is None


# --- API contracts -------------------------------------------------------------


async def test_forecast_readiness_endpoint(client):
    r = await client.get("/api/research/forecast/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["methodology_status"] == "experimental"
    assert set(body["models"]) >= {"model_a_equal"}
    for m in body["models"].values():
        assert {h["horizon"] for h in m["horizons"]} == {
            "1y", "2y", "5y", "10y"
        }
        # contract: an unavailable horizon always carries a reason
        for h in m["horizons"]:
            if not h["available"]:
                assert h["unavailable_reason"]


async def test_country_forecast_never_emits_probability(client):
    r = await client.get("/api/research/forecast/USA?model=model_a_equal&horizon=5y")
    assert r.status_code == 200
    body = r.json()
    f = body["forecast"]
    if not f["available"]:
        assert f["stage_probabilities"] is None
        assert f["unavailable_reason"]


async def test_country_forecast_rejects_bad_horizon(client):
    r = await client.get("/api/research/forecast/USA?horizon=3y")
    assert r.status_code == 422


async def test_country_forecast_rejects_bad_model(client):
    r = await client.get("/api/research/forecast/USA?model=nope")
    assert r.status_code == 404
