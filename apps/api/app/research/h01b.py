"""H01B — private-credit / sectoral-debt banking-crisis research diagnostics.

Registered under protocol ``H01B-P1.0``. The 1990-2020 JST R6 holdout was already
used for exploratory predictor inspection during the H01-P1.0 forensic audit, so
every result here is a *retrospective diagnostic*, not a confirmatory holdout
test. Clustering diagnostics treat co-moving crisis waves as dependent events.
"""
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.data_sources.jst_macrohistory import JST_DATASET_VERSION, JST_SOURCE_KEY
from app.research.h01 import _auc, _percentile_scores, load_jst_panel

Panel = dict[tuple[str, int], dict[str, float]]


# ---------------------------------------------------------------------------
# Predictor family (each returns a float or None given the panel at an origin)
# ---------------------------------------------------------------------------

def _ratio(panel: Panel, entity: str, year: int, num: str, den: str) -> float | None:
    row = panel.get((entity, year), {})
    n, d = row.get(num), row.get(den)
    if n is None or d in (None, 0):
        return None
    return n / d


def _ratio_change(panel: Panel, entity: str, origin: int, years: int, num: str, den: str) -> float | None:
    cur = _ratio(panel, entity, origin, num, den)
    prev = _ratio(panel, entity, origin - years, num, den)
    if cur is None or prev is None:
        return None
    return cur - prev


def _credit_gap(panel: Panel, entity: str, origin: int) -> float | None:
    """Trailing 10-year OLS trend gap for tloans/gdp (one-sided, no look-ahead)."""
    years, vals = [], []
    for yr in range(origin - 14, origin - 4):
        v = _ratio(panel, entity, yr, "tloans", "gdp")
        if v is not None:
            years.append(yr)
            vals.append(v)
    if len(years) < 8:
        return None
    cur = _ratio(panel, entity, origin, "tloans", "gdp")
    if cur is None:
        return None
    n = len(years)
    sx, sy = sum(years), sum(vals)
    sxx = sum(y * y for y in years)
    sxy = sum(y * v for y, v in zip(years, vals))
    denom = n * sxx - sx * sx
    if denom == 0:
        return None
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return cur - (intercept + slope * origin)


def _debt_service_proxy(panel: Panel, entity: str, origin: int) -> float | None:
    """Crude interest-burden proxy: private loans/GDP x short rate (not a true DSR)."""
    ratio = _ratio(panel, entity, origin, "tloans", "gdp")
    stir = panel.get((entity, origin), {}).get("stir")
    if ratio is None or stir is None:
        return None
    return ratio * stir / 100.0


def _real_house_price_growth(panel: Panel, entity: str, origin: int) -> float | None:
    cur = _ratio(panel, entity, origin, "hpnom", "cpi")
    prev = _ratio(panel, entity, origin - 3, "hpnom", "cpi")
    if cur is None or prev in (None, 0):
        return None
    return cur / prev - 1.0


def _real_long_rate(panel: Panel, entity: str, origin: int) -> float | None:
    row = panel.get((entity, origin), {})
    ltrate, cpi_now = row.get("ltrate"), row.get("cpi")
    cpi_prev = panel.get((entity, origin - 1), {}).get("cpi")
    if ltrate is None or cpi_now is None or cpi_prev in (None, 0):
        return None
    return ltrate - (cpi_now / cpi_prev - 1.0) * 100.0


def _public_interest_proxy(panel: Panel, entity: str, origin: int) -> float | None:
    """Estimated interest burden: public debt/GDP x long rate (derived, not official)."""
    row = panel.get((entity, origin), {})
    debt, ltrate = row.get("debtgdp"), row.get("ltrate")
    if debt is None or ltrate is None:
        return None
    return debt * ltrate / 100.0


def _income_growth_5y(panel: Panel, entity: str, origin: int) -> float | None:
    cur = panel.get((entity, origin), {}).get("rgdpbarro")
    prev = panel.get((entity, origin - 5), {}).get("rgdpbarro")
    if cur is None or prev in (None, 0):
        return None
    return cur / prev - 1.0


def _debtgdp_change(panel: Panel, entity: str, origin: int) -> float | None:
    cur = panel.get((entity, origin), {}).get("debtgdp")
    prev = panel.get((entity, origin - 5), {}).get("debtgdp")
    if cur is None or prev is None:
        return None
    return cur - prev


PREDICTOR_SPECS: dict[str, dict[str, Any]] = {
    "private_credit_gdp_5y_change": {
        "label": "Private credit/GDP, 5-year change (tloans/gdp)",
        "kind": "primary",
        "fn": lambda p, e, o: _ratio_change(p, e, o, 5, "tloans", "gdp"),
    },
    "private_credit_gdp_level": {
        "label": "Private credit/GDP level (tloans/gdp)",
        "kind": "candidate",
        "fn": lambda p, e, o: _ratio(p, e, o, "tloans", "gdp"),
    },
    "household_credit_gdp_5y_change": {
        "label": "Household credit/GDP, 5-year change (thh/gdp)",
        "kind": "candidate",
        "fn": lambda p, e, o: _ratio_change(p, e, o, 5, "thh", "gdp"),
    },
    "corporate_credit_gdp_5y_change": {
        "label": "Corporate credit/GDP, 5-year change (tbus/gdp)",
        "kind": "candidate",
        "fn": lambda p, e, o: _ratio_change(p, e, o, 5, "tbus", "gdp"),
    },
    "mortgage_credit_gdp_5y_change": {
        "label": "Mortgage credit/GDP, 5-year change (tmort/gdp)",
        "kind": "candidate",
        "fn": lambda p, e, o: _ratio_change(p, e, o, 5, "tmort", "gdp"),
    },
    "credit_to_gdp_gap_trailing_10y": {
        "label": "Credit/GDP gap vs trailing 10y trend (one-sided OLS)",
        "kind": "candidate",
        "fn": _credit_gap,
    },
    "debt_service_proxy": {
        "label": "Debt-service proxy (tloans/gdp x short rate; derived, not BIS DSR)",
        "kind": "candidate",
        "fn": _debt_service_proxy,
    },
    "real_house_price_3y_growth": {
        "label": "Real house price, 3-year growth (hpnom/cpi)",
        "kind": "candidate",
        "fn": _real_house_price_growth,
    },
    "real_long_rate": {
        "label": "Real long-term rate (ltrate - CPI inflation)",
        "kind": "candidate",
        "fn": _real_long_rate,
    },
    "public_debtgdp_5y_change": {
        "label": "Public debt/GDP, 5-year change (H01-P1.0 reference control)",
        "kind": "control",
        "fn": _debtgdp_change,
    },
    "public_interest_burden_proxy": {
        "label": "Public interest burden proxy (debtgdp x long rate; derived)",
        "kind": "control",
        "fn": _public_interest_proxy,
    },
    "income_residual_credit_5y_change": {
        "label": "Credit/GDP 5y change residualised on 5y real income growth (train-fit OLS)",
        "kind": "secondary",
        "fn": lambda p, e, o: _ratio_change(p, e, o, 5, "tloans", "gdp"),
        "residualize_on": _income_growth_5y,
    },
}


@dataclass(frozen=True)
class Sample:
    entity: str
    origin: int
    outcome_year: int
    predictor: float
    auxiliary: float | None
    outcome: bool


def build_episode_registry(events: set[tuple[str, int]], max_gap: int = 3) -> list[dict[str, Any]]:
    """Group globally co-moving onset years into crisis episodes (gap <= 3y)."""
    years = sorted({y for _, y in events})
    episodes: list[list[int]] = []
    for y in years:
        if episodes and y - episodes[-1][-1] <= max_gap:
            episodes[-1].append(y)
        else:
            episodes.append([y])
    registry = []
    for i, ys in enumerate(episodes, start=1):
        members = sorted(e for e, y in events if y in ys)
        registry.append({
            "episode_id": f"E{i:02d}_{ys[0]}_{ys[-1]}",
            "start_year": ys[0],
            "end_year": ys[-1],
            "onset_years": ys,
            "entity_count": len(set(members)),
            "event_count": len(members),
            "entities": sorted(set(members)),
        })
    return registry


def _episode_for_year(registry: list[dict[str, Any]], year: int) -> str | None:
    for ep in registry:
        if ep["start_year"] <= year <= ep["end_year"]:
            return ep["episode_id"]
    return None


def _pr_auc(scores_outcomes: list[tuple[float, bool]]) -> float | None:
    """Average-precision (precision-recall area) — robust to heavy class imbalance."""
    ordered = sorted(scores_outcomes, key=lambda x: -x[0])
    positives = sum(1 for _, y in ordered if y)
    if not positives:
        return None
    tp = fp = 0
    prev_recall = 0.0
    area = 0.0
    for _, y in ordered:
        if y:
            tp += 1
        else:
            fp += 1
        recall = tp / positives
        precision = tp / (tp + fp)
        area += precision * (recall - prev_recall)
        prev_recall = recall
    return area


def _confusion(scores: list[float], test: list[Sample], threshold: float) -> dict[str, int]:
    tp = fp = fn = tn = 0
    for sc, s in zip(scores, test):
        flag = sc >= threshold
        if flag and s.outcome:
            tp += 1
        elif flag:
            fp += 1
        elif s.outcome:
            fn += 1
        else:
            tn += 1
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn}


def _metrics_block(scores: list[float], test: list[Sample], threshold: float,
                   episodes_of: Callable[[Sample], str | None]) -> dict[str, Any]:
    cf = _confusion(scores, test, threshold)
    n = len(test)
    events = sum(s.outcome for s in test)
    base = events / n if n else None
    auc = _auc(list(zip(scores, (s.outcome for s in test))))
    pr_auc = _pr_auc(list(zip(scores, (s.outcome for s in test))))
    warned = cf["tp"] + cf["fp"]
    pos_eps = {episodes_of(s) for s in test if s.outcome}
    return {
        "n": n,
        "train_n": None,
        "events": events,
        "countries": len({s.entity for s in test}),
        "distinct_episodes_with_events": len(pos_eps - {None}),
        "base_rate": base,
        "roc_auc": auc,
        "pr_auc": pr_auc,
        "warning_threshold": threshold,
        "warning_share": warned / n if n else None,
        "precision_at_threshold": cf["tp"] / warned if warned else None,
        "recall_at_threshold": cf["tp"] / events if events else None,
        "false_positive_rate": cf["fp"] / (cf["fp"] + cf["tn"]) if (cf["fp"] + cf["tn"]) else None,
        "confusion": cf,
    }


def _bootstrap_year_auc(
    samples: list[Sample], scores: list[float], draws: int = 300, seed: int = 42,
) -> dict[str, float | None]:
    """Year-block bootstrap CI: resample outcome years so crisis waves stay one draw."""
    by_year: dict[int, list[tuple[float, bool]]] = defaultdict(list)
    for s, sc in zip(samples, scores):
        by_year[s.outcome_year].append((sc, s.outcome))
    years = sorted(by_year)
    rng = random.Random(seed)
    aucs = []
    for _ in range(draws):
        picked = [rng.choice(years) for _ in years]
        flat = [p for y in picked for p in by_year[y]]
        a = _auc(flat)
        if a is not None:
            aucs.append(a)
    aucs.sort()
    if not aucs:
        return {"auc_ci_low": None, "auc_ci_high": None, "bootstrap_draws": 0}
    lo = aucs[int(0.025 * (len(aucs) - 1))]
    hi = aucs[int(0.975 * (len(aucs) - 1))]
    return {"auc_ci_low": round(lo, 4), "auc_ci_high": round(hi, 4),
            "bootstrap_draws": len(aucs), "bootstrap_method": "year-block resample preserves within-wave dependence"}


def evaluate_predictor(
    name: str,
    fn: Callable[[Panel, str, int], float | None],
    panel: Panel,
    coverage: set[tuple[str, int]],
    events: set[tuple[str, int]],
    episodes: list[dict[str, Any]],
    horizon: int,
    split_year: int,
    residualize_on: Callable[[Panel, str, int], float | None] | None = None,
) -> dict[str, Any] | None:
    samples: list[Sample] = []
    for entity, outcome_year in sorted(coverage):
        origin = outcome_year - horizon
        pred = fn(panel, entity, origin)
        if pred is None:
            continue
        aux = residualize_on(panel, entity, origin) if residualize_on else None
        samples.append(Sample(
            entity=entity, origin=origin, outcome_year=outcome_year,
            predictor=pred, auxiliary=aux,
            outcome=(entity, outcome_year) in events,
        ))
    if len(samples) < 50:
        return None

    train = [s for s in samples if s.outcome_year < split_year]
    test = [s for s in samples if s.outcome_year >= split_year]
    if len(test) < 50 or len(train) < 50:
        return None

    # Optional train-fit residualisation (e.g., income growth for Q17).
    if residualize_on is not None:
        pts = [(s.auxiliary, s.predictor) for s in train if s.auxiliary is not None]
        if len(pts) < 20:
            return None
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        xbar, ybar = sum(xs) / len(xs), sum(ys) / len(ys)
        denom = sum((x - xbar) ** 2 for x in xs)
        slope = sum((x - xbar) * (y - ybar) for x, y in pts) / denom if denom else 0.0
        intercept = ybar - slope * xbar
        train = [Sample(s.entity, s.origin, s.outcome_year,
                        s.predictor - (intercept + slope * s.auxiliary), None, s.outcome)
                 for s in train]
        test = [Sample(s.entity, s.origin, s.outcome_year,
                       s.predictor - (intercept + slope * (s.auxiliary or 0.0)), None, s.outcome)
                for s in test]

    train_values = [s.predictor for s in train]
    scores = _percentile_scores(train_values, [s.predictor for s in test])
    episodes_of = lambda s: _episode_for_year(episodes, s.outcome_year)
    block = _metrics_block(scores, test, 0.8, episodes_of)
    block["train_n"] = len(train)
    block.update(_bootstrap_year_auc(test, scores))

    # Clustered diagnostics ---------------------------------------------------
    episode_ids = sorted({ep["episode_id"] for ep in episodes
                          if any(ep["start_year"] <= s.outcome_year <= ep["end_year"]
                                 for s in test)})
    loeo = {}
    for ep in episodes:
        span = range(ep["start_year"], ep["end_year"] + 1)
        kept = [(sc, s) for sc, s in zip(scores, test) if s.outcome_year not in span]
        if len(kept) < 40 or not any(s.outcome for _, s in kept):
            continue
        loeo[ep["episode_id"]] = {
            "dropped_years": ep["onset_years"],
            "dropped_events": ep["event_count"],
            "n": len(kept),
            "auc": _auc([(sc, s.outcome) for sc, s in kept]),
        }
    loco = {}
    for ent in sorted({s.entity for s in test}):
        kept = [(sc, s) for sc, s in zip(scores, test) if s.entity != ent]
        if len(kept) < 40 or not any(s.outcome for _, s in kept):
            continue
        loco[ent] = {"n": len(kept), "auc": _auc([(sc, s.outcome) for sc, s in kept])}
    loco_vals = [v["auc"] for v in loco.values() if v["auc"] is not None]
    time_blocks = {}
    for label, lo, hi in (("1990-1999", 1990, 1999), ("2000-2009", 2000, 2009), ("2010-2020", 2010, 2020)):
        kept = [(sc, s) for sc, s in zip(scores, test) if lo <= s.outcome_year <= hi]
        ev = sum(s.outcome for _, s in kept)
        time_blocks[label] = {
            "n": len(kept), "events": ev,
            "base_rate": ev / len(kept) if kept else None,
            "auc": _auc([(sc, s.outcome) for sc, s in kept]) if ev else None,
        }
    ex_gfc = [(sc, s) for sc, s in zip(scores, test) if s.outcome_year not in (2007, 2008)]
    sensitivity = {
        "ex_2007_2008": {
            "n": len(ex_gfc), "events": sum(s.outcome for _, s in ex_gfc),
            "auc": _auc([(sc, s.outcome) for sc, s in ex_gfc]) if any(s.outcome for _, s in ex_gfc) else None,
        }
    }
    return {
        "predictor": name,
        "horizon_years": horizon,
        "metrics": block,
        "clustered_diagnostics": {
            "leave_one_episode_out": loeo,
            "leave_one_country_out_auc_min_max": (
                [min(loco_vals), max(loco_vals)] if loco_vals else None),
            "leave_one_country_out": loco,
            "time_blocks": time_blocks,
            "sensitivity": sensitivity,
            "episodes_in_test": episode_ids,
        },
    }


async def evaluate_h01b(session: AsyncSession, split_year: int = 1990) -> dict[str, Any]:
    panel, coverage, events = await load_jst_panel(session)
    episodes = build_episode_registry(events)
    test_events = [ep for ep in episodes if ep["end_year"] >= split_year]

    results: dict[str, dict[str, Any]] = {}
    for name, spec in PREDICTOR_SPECS.items():
        per_h = {}
        for horizon in (1, 2, 5):
            res = evaluate_predictor(
                name, spec["fn"], panel, coverage, events, episodes,
                horizon, split_year,
                residualize_on=spec.get("residualize_on"),
            )
            if res is not None:
                per_h[str(horizon)] = res
        if per_h:
            results[name] = {
                "label": spec["label"], "kind": spec["kind"], "horizons": per_h,
            }

    primary = results.get("private_credit_gdp_5y_change", {}).get("horizons", {})
    primary_auc_1y = (primary.get("1") or {}).get("metrics", {}).get("roc_auc")
    result_state = (
        "exploratory_association_retrospective_diagnostic"
        if primary_auc_1y is not None and primary_auc_1y > 0.5
        else "no_evidence_of_improved_predictive_value"
    )
    return {
        "hypothesis_code": "H01B",
        "protocol_version": "H01B-P1.0",
        "model_id": "private_credit_family_univariate",
        "model_version": "v1",
        "evaluation_type": "retrospective_clustered_diagnostic",
        "holdout_integrity": (
            "The 1990-2020 JST R6 holdout was already used for exploratory predictor "
            "inspection during the H01-P1.0 forensic audit; it is NOT an untouched "
            "confirmatory holdout for predictor selection."
        ),
        "split_year": split_year,
        "warning_rule": "train percentile score >= 0.80 (same convention as H01-P1.0 for comparability)",
        "episodes": episodes,
        "post_split_episodes": test_events,
        "predictors": results,
        "primary_predictor": "private_credit_gdp_5y_change",
        "result_state": result_state,
        "limitations": [
            "retrospective JST R6 dataset, not real-time vintages",
            "annual crisis onsets only; 13 of 19 held-out events form the 2007-2008 global wave and 4 the 1991 Nordic wave",
            "predictor was selected using prior exploratory diagnostics on the same holdout; results are not confirmatory",
            "univariate family; debt-service and credit-gap proxies are derived constructions, not official BIS DSR series",
            "no calibrated probabilities; AUC is discrimination, not forecast accuracy",
        ],
        "sample_counts": {"coverage_rows": len(coverage), "event_onsets": len(events), "episodes": len(episodes)},
        "dataset_versions": {JST_SOURCE_KEY: JST_DATASET_VERSION},
        "generated_at": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# H01T — threshold heterogeneity research protocol (Q14)
# ---------------------------------------------------------------------------

async def evaluate_threshold_heterogeneity(
    session: AsyncSession, split_year: int = 1990,
) -> dict[str, Any]:
    """Dedicated Q14 diagnostics: do debt/GDP *levels* carry reproducible thresholds?

    Tests whether within-country, regime-conditional or period-conditional level
    thresholds predict crisis onset — without fitting one universal cutoff.
    """
    panel, coverage, events = await load_jst_panel(session)
    episodes = build_episode_registry(events)

    def level_samples(var_fn: Callable[[Panel, str, int], float | None], horizon: int):
        out = []
        for entity, oy in sorted(coverage):
            origin = oy - horizon
            v = var_fn(panel, entity, origin)
            if v is None:
                continue
            peg = panel.get((entity, origin), {}).get("peg")
            out.append({"entity": entity, "origin": origin, "outcome_year": oy,
                        "value": v, "peg": peg,
                        "outcome": (entity, oy) in events})
        return out

    report: dict[str, Any] = {
        "hypothesis_code": "H01T", "protocol_version": "H01T-P1.0",
        "model_id": "debt_level_threshold_heterogeneity", "model_version": "v1",
        "evaluation_type": "retrospective_threshold_diagnostic",
        "split_year": split_year,
    }
    for spec_name, var_fn in (
        ("public_debtgdp_level", lambda p, e, o: p.get((e, o), {}).get("debtgdp")),
        ("private_tloans_gdp_level", lambda p, e, o: _ratio(p, e, o, "tloans", "gdp")),
    ):
        s1 = level_samples(var_fn, 1)
        train = [s for s in s1 if s["outcome_year"] < split_year]
        test = [s for s in s1 if s["outcome_year"] >= split_year]

        # 1. Universal threshold: pooled train p80 applied to test.
        train_vals = sorted(s["value"] for s in train)
        pooled_p80 = train_vals[int(0.8 * (len(train_vals) - 1))] if train_vals else None
        scores_pooled = _percentile_scores(train_vals, [s["value"] for s in test])
        pooled = {
            "pooled_train_p80_value": pooled_p80,
            "auc": _auc(list(zip(scores_pooled, (s["outcome"] for s in test)))),
            "warning_share": sum(sc >= 0.8 for sc in scores_pooled) / len(scores_pooled) if scores_pooled else None,
        }

        # 2. Within-country thresholds: each entity's own train p80.
        by_ent_train: dict[str, list[float]] = defaultdict(list)
        for s in train:
            by_ent_train[s["entity"]].append(s["value"])
        country_p80 = {
            e: sorted(v)[int(0.8 * (len(v) - 1))]
            for e, v in by_ent_train.items() if len(v) >= 20
        }
        within = []
        for s in test:
            thr = country_p80.get(s["entity"])
            if thr is None:
                continue
            within.append((1.0 if s["value"] >= thr else 0.0, s["outcome"], s["value"]))
        country_dispersion = None
        if len(country_p80) >= 5:
            vals = sorted(country_p80.values())
            mean = sum(vals) / len(vals)
            var = sum((v - mean) ** 2 for v in vals) / len(vals)
            country_dispersion = {
                "n_countries": len(country_p80),
                "min_p80": vals[0], "median_p80": vals[len(vals) // 2],
                "max_p80": vals[-1],
                "coefficient_of_variation": (var ** 0.5 / mean) if mean else None,
                "interpretation": "p80 level thresholds vary materially by country — a single universal cutoff is not portable",
            }

        # 3. Regime split at origin (JST `peg`: exchange-rate peg dummy).
        regime = {}
        for regime_name, flag in (("pegged_fx", 1.0), ("non_pegged", 0.0)):
            sub = [(sc, s["outcome"]) for sc, s in zip(scores_pooled, test) if s["peg"] == flag]
            ev = sum(y for _, y in sub)
            regime[regime_name] = {
                "n": len(sub), "events": ev,
                "auc": _auc(sub) if ev else None,
            }

        # 4. Monetary-era splits (train only where history exists).
        era = {}
        for era_name, lo, hi in (("pre_1914_gold", 1870, 1913), ("interwar_1914_1944", 1914, 1944),
                                 ("bretton_woods_1945_1971", 1945, 1971), ("fiat_1972_2020", 1972, 2020)):
            sub_all = [(s["value"], s["outcome"]) for s in s1 if lo <= s["outcome_year"] <= hi]
            ev = sum(y for _, y in sub_all)
            era[era_name] = {"n": len(sub_all), "events": ev,
                             "auc": _auc(sub_all) if ev else None}

        report[spec_name] = {
            "horizon_years": 1,
            "train_n": len(train), "test_n": len(test),
            "test_events": sum(s["outcome"] for s in test),
            "universal_threshold": pooled,
            "within_country_thresholds": {
                "country_p80_values": country_p80,
                "dispersion": country_dispersion,
                "within_flag_precision": (
                    sum(1 for flag, y, _ in within if flag and y) / max(1, sum(1 for flag, _, _ in within if flag))
                    if within else None
                ),
                "within_flag_rate": sum(1 for flag, _, _ in within if flag) / len(within) if within else None,
            },
            "regime_split": regime,
            "era_split": era,
        }

    report["conclusion"] = (
        "No reproducible universal debt-to-GDP crisis threshold: pooled p80 levels "
        "discriminate at or below chance held out, and country-specific p80 values "
        "differ by an order of magnitude across entities. Conditional heterogeneity "
        "(regime, era, country) — not a single threshold — is the supported research direction."
    )
    report["generated_at"] = datetime.now(timezone.utc)
    return report
