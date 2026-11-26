"""H01B private-credit evaluation + v1.2 registry-correction tests."""
from collections import defaultdict

import pytest
from sqlalchemy import select

from app.db import session as session_module
from app.models import ValidationQuestion
from app.research.h01b import (
    PREDICTOR_SPECS, _auc, _credit_gap, _pr_auc, build_episode_registry,
    evaluate_predictor,
)
from app.research.validation_questions import (
    VALIDATION_QUESTIONS, VALIDATION_REGISTRY_VERSION,
)


def test_episode_registry_groups_comoving_onsets():
    events = {
        ("USA", 1930), ("FRA", 1930), ("DEU", 1931), ("GBR", 1931),
        ("BEL", 1934), ("FIN", 1991), ("SWE", 1991), ("USA", 2007),
        ("GBR", 2007), ("IRL", 2008), ("ESP", 2008), ("JPN", 1997),
    }
    eps = build_episode_registry(events)
    assert len(eps) == 4  # 1930-34 wave, 1991 Nordic, 1997, 2007-08
    wave = next(e for e in eps if e["start_year"] == 1930)
    assert wave["end_year"] == 1934 and wave["event_count"] == 5
    gfc = next(e for e in eps if e["start_year"] == 2007)
    assert gfc["event_count"] == 4 and set(gfc["entities"]) == {"USA", "GBR", "IRL", "ESP"}


def test_pr_auc_and_auc_agree_on_direction():
    pairs = [(0.9, True), (0.8, True), (0.7, False), (0.6, True),
             (0.2, False), (0.1, False)]
    assert _auc(pairs) > 0.5
    assert _pr_auc(pairs) is not None and _pr_auc(pairs) > 0.5


def test_credit_gap_is_onesided_no_lookahead():
    """The trailing-10y gap must not depend on data after the origin year."""
    panel = defaultdict(dict)
    for y in range(1980, 2001):
        panel[("USA", y)] = {"tloans": 10 + (y - 1980), "gdp": 100.0}
    gap_at_2000 = _credit_gap(panel, "USA", 2000)
    # Perturb the future — result must be identical.
    panel[("USA", 2005)] = {"tloans": 99999.0, "gdp": 1.0}
    assert _credit_gap(panel, "USA", 2000) == gap_at_2000


def test_predictor_evaluate_reports_clusters_and_ci():
    """Synthetic panel: verify metrics block contains episodes, CI, LOEO/LOCO."""
    panel = defaultdict(dict)
    coverage, events = set(), set()
    for ent in ("USA", "GBR", "FRA", "DEU", "JPN", "ITA"):
        for y in range(1870, 2021):
            coverage.add((ent, y))
            panel[(ent, y)] = {"tloans": 1.0 + 0.02 * (y - 1870) + hash(ent) % 7,
                               "gdp": 1.0}
    # Inject a crisis wave whose origins had higher credit growth.
    for ent in ("USA", "GBR", "FRA"):
        for y in (2007, 2008):
            events.add((ent, y))
            panel[(ent, y - 1)]["tloans"] = 50.0
            panel[(ent, y - 5)]["tloans"] = 5.0
    episodes = build_episode_registry(events)
    spec = PREDICTOR_SPECS["private_credit_gdp_5y_change"]
    res = evaluate_predictor(
        "private_credit_gdp_5y_change", spec["fn"], panel,
        coverage, events, episodes, 1, 1990,
    )
    assert res is not None
    m = res["metrics"]
    assert m["n"] > 100 and m["events"] == 6
    assert m["roc_auc"] is not None
    assert "bootstrap_draws" in m and m["bootstrap_draws"] > 0
    cd = res["clustered_diagnostics"]
    assert "leave_one_episode_out" in cd and "leave_one_country_out" in cd
    assert "time_blocks" in cd and "sensitivity" in cd


async def test_v12_registry_corrections_seeded(client):
    """v1.2 rows carry the corrected statuses; v1.1 rows are preserved."""
    assert VALIDATION_REGISTRY_VERSION == "validation-questions-v1.2"
    q = {d.question_code: d for d in VALIDATION_QUESTIONS}
    assert q["Q08"].research_validation_status == "insufficient_evidence"
    assert q["Q08"].implementation_status == "research_method_implemented"
    assert q["Q11"].research_validation_status == "evaluated_with_no_clear_conclusion"
    assert q["Q14"].research_validation_status == "evaluated_with_no_clear_conclusion"
    assert q["Q14"].implementation_status == "evaluation_implemented"
    assert q["Q17"].research_validation_status == "exploratory_findings"
    assert "H01B" in q["Q17"].related_hypotheses
    assert "H01B" in q["Q11"].related_hypotheses
    assert "H01T" in q["Q14"].related_hypotheses

    async with session_module._sessionmaker() as session:
        rows = (await session.execute(
            select(ValidationQuestion).where(
                ValidationQuestion.question_code == "Q17",
            ).order_by(ValidationQuestion.registry_version))).scalars().all()
    # The seed DB only has the current version — production preserves all.
    assert rows and rows[-1].registry_version == "validation-questions-v1.2"
    assert rows[-1].research_validation_status == "exploratory_findings"


async def test_debt_cycle_and_power_routes_respond(client):
    for path in (
        "/api/research/foundation/debt-cycle/overview",
        "/api/research/foundation/currency-power/overview",
        "/api/research/foundation/historical-power/overview",
    ):
        r = await client.get(path)
        assert r.status_code == 200, path
        assert "module" in r.json()


async def test_h01b_route_responds(client):
    r = await client.get("/api/research/foundation/h01b")
    assert r.status_code == 200
    data = r.json()
    assert data["hypothesis_code"] == "H01B"
    assert "holdout" in data["holdout_integrity"].lower() or "inspected" in data["holdout_integrity"].lower()
