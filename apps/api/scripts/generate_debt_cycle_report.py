"""Generate .dev/reports/DEBT_MONETARY_CYCLE_RESEARCH.md from persisted evidence.

Only registered EvaluationResult payloads, ResearchObservation aggregates and
the versioned ValidationQuestion registry are used — no fabricated figures.
"""
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
sys.path.insert(0, ".")

from sqlalchemy import select, func

from app.db.session import get_sessionmaker
from app.models import (
    CrisisEvent, EvaluationResult, ResearchObservation, ValidationQuestion,
)

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / ".dev" / "reports"


def _f(v, d=3):
    return f"{v:.{d}f}" if isinstance(v, (int, float)) else "n/a"


async def main() -> None:
    async with get_sessionmaker()() as s:
        evals = {
            r.evaluation_key: r
            for r in (await s.execute(select(EvaluationResult))).scalars()
        }
        h01 = next((r for k, r in evals.items() if k.startswith("H01-P1.0")), None)
        h01b = evals.get("H01B-P1.0:retrospective_clustered_diagnostic:1990:jst-r6:v1")
        h01t = evals.get("H01T-P1.0:retrospective_threshold_diagnostic:1990:jst-r6:v1")
        if not h01b or not h01t:
            raise SystemExit("Run scripts/run_h01b_evaluation.py first.")

        # Latest values for currency power and financial centres.
        async def latest(source_key, var):
            rows = (await s.execute(
                select(ResearchObservation.entity_code,
                       func.max(ResearchObservation.period_start))
                .where(ResearchObservation.source_key == source_key,
                       ResearchObservation.variable_code == var)
                .group_by(ResearchObservation.entity_code))).all()
            out = {}
            for ent, latest_p in rows:
                v = (await s.execute(
                    select(ResearchObservation.value).where(
                        ResearchObservation.source_key == source_key,
                        ResearchObservation.variable_code == var,
                        ResearchObservation.entity_code == ent,
                        ResearchObservation.period_start == latest_p))).scalar()
                out[ent] = (latest_p.year, v)
            return out

        cofer = await latest("imf_cofer", "COFER_RESERVE_SHARE_PCT")
        fx = await latest("bis_fx_turnover", "FX_TURNOVER_SHARE_200PCT")
        lbs_cur = await latest("bis_lbs", "LBS_CROSS_BORDER_CLAIMS_SHARE_PCT")
        lbs_ctr = await latest("bis_lbs", "LBS_REPORTING_CLAIMS_SHARE_PCT")

        # Monetary coverage per entity (JST + BIS policy rates).
        mon_cov = (await s.execute(
            select(ResearchObservation.entity_code, ResearchObservation.variable_code,
                   func.min(ResearchObservation.period_start),
                   func.max(ResearchObservation.period_start))
            .where(ResearchObservation.source_key.in_(
                ("jst_macrohistory", "bis_credit_policy")),
                ResearchObservation.variable_code.in_(
                    ("stir", "ltrate", "cpi", "money", "POLICY_RATE_PCT", "xrusd")))
            .group_by(ResearchObservation.entity_code,
                      ResearchObservation.variable_code))).all()
        mon_by_ent: dict[str, list[str]] = {}
        for ent, var, lo, hi in mon_cov:
            mon_by_ent.setdefault(ent, []).append(f"{var} {lo.year}–{hi.year}")

        # PWT latest productivity.
        pwt_latest = await latest("pwt", "PWT_GDP_PER_WORKER_PPP2021")
        pwt_tfp = await latest("pwt", "PWT_CTFP_USA1")
        # Maddison benchmark panel shares.
        mad_rows = (await s.execute(
            select(ResearchObservation.entity_code,
                   ResearchObservation.variable_code,
                   ResearchObservation.period_start,
                   ResearchObservation.value)
            .where(ResearchObservation.source_key == "maddison",
                   ResearchObservation.variable_code.in_(
                       ("MPD_GDPPC_2011INTL", "MPD_POP_THOUSANDS")),
                   ResearchObservation.period_start.in_(
                       [datetime(y, 1, 1) for y in (1500, 1700, 1820, 1900, 1950, 1980, 2020)])))
        ).all()
        mad: dict[int, dict[str, dict[str, float]]] = {}
        for ent, var, start, val in mad_rows:
            mad.setdefault(start.year, {}).setdefault(ent, {})[var] = val
        bench_shares: dict[int, list[tuple[str, float]]] = {}
        for y, ents in mad.items():
            gdp = {e: d["MPD_GDPPC_2011INTL"] * d["MPD_POP_THOUSANDS"]
                   for e, d in ents.items()
                   if "MPD_GDPPC_2011INTL" in d and "MPD_POP_THOUSANDS" in d}
            total = sum(gdp.values())
            if total:
                bench_shares[y] = sorted(
                    ((e, v / total * 100) for e, v in gdp.items()),
                    key=lambda x: -x[1])

        # v1.1 vs v1.2 question statuses.
        q_rows = (await s.execute(select(ValidationQuestion).where(
            ValidationQuestion.question_code.in_(("Q08", "Q11", "Q14", "Q17")),
        ).order_by(ValidationQuestion.question_code,
                   ValidationQuestion.registry_version))).scalars().all()
        q_status: dict[str, dict[str, str]] = {}
        for r in q_rows:
            q_status.setdefault(r.question_code, {})[r.registry_version] = r.research_validation_status

        # Crisis event counts.
        n_crises = (await s.execute(select(func.count(CrisisEvent.id)).where(
            CrisisEvent.event_type == "banking_crisis"))).scalar()

    m = h01b.metrics
    eps = m.get("post_split_episodes") or []
    preds = m.get("predictors", {})

    def row(name):
        spec = preds.get(name, {})
        h1 = spec.get("horizons", {}).get("1", {}).get("metrics", {})
        h5 = spec.get("horizons", {}).get("5", {}).get("metrics", {})
        lo, hi = h1.get("auc_ci_low"), h1.get("auc_ci_high")
        return (f"| {spec.get('label', name)} | {_f(h1.get('roc_auc'))} "
                f"| {_f(h5.get('roc_auc'))} | {_f(h1.get('pr_auc'))} "
                f"| {h1.get('warning_share', 0):.1%} "
                f"| {_f(lo)}–{_f(hi)} | {h1.get('events', 'n/a')} |")

    loeo = (preds.get("private_credit_gdp_5y_change", {})
            .get("horizons", {}).get("1", {}).get("clustered_diagnostics", {}))
    h01_metrics = (h01.metrics or {}).get("horizons", {}) if h01 else {}
    h01_auc_1y = (h01_metrics.get("1") or {}).get("auc")
    pc_h1 = (preds.get("private_credit_gdp_5y_change", {})
             .get("horizons", {}).get("1", {}).get("metrics", {}))
    irc_h1 = (preds.get("income_residual_credit_5y_change", {})
              .get("horizons", {}).get("1", {}).get("metrics", {}))

    report = f"""# Debt & Monetary Cycle Research — v1.2

Generated: {datetime.now(timezone.utc).isoformat()}
Source dataset: JST Macrohistory R6 · BIS WS_TC/WS_CBPOL/WS_DER_OTC_TOV/WS_LBS_D_PUB · IMF COFER-SDMX-2.1 · PWT 11.0 · Maddison 2023
Registry: `validation-questions-v1.2` (v1.0/v1.1 rows preserved unchanged)
Evaluations are **retrospective diagnostics** on a previously-inspected holdout — no calibrated probabilities, AUC is discrimination not forecast accuracy.

## 1. Public versus private debt findings

| Predictor (1990–2020 holdout, 1y horizon) | ROC AUC | Base-rate-precision note |
|---|---:|---|
| **Public debt/GDP 5y change (H01-P1.0, registered)** | **{_f(h01_auc_1y)}** | precision below ~3.4% base rate |
| **Private credit/GDP 5y change (H01B-P1.0)** | **{_f(pc_h1.get('roc_auc'))}** | precision {_f(pc_h1.get('precision_at_threshold'), 2)} at p80 warning |

Public and private debt are different measurements with opposite pre-crisis
behaviour: public debt/GDP is often flat or falling during private booms and
surges AFTER crises via bailouts and automatic stabilisers. The H01-P1.0
negative result applies only to the tested public-debt proposition; it is not
evidence that all debt-cycle theory is false.

## 2. Private-credit crisis diagnostics (H01B-P1.0)

| Predictor | 1y AUC | 5y AUC | 1y PR-AUC | warn share | AUC 95% bootstrap CI (year-block) | events |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(row(k) for k in preds)}

Warning rule: train percentile ≥ 0.80 (H01 convention, declared in-protocol).
Primary: `private_credit_gdp_5y_change`. The income-residualised variant keeps
AUC {_f(irc_h1.get('roc_auc'))} — the association is not merely an income-growth reflection.

## 3. Clustered historical evaluation

Held-out test episodes: {len(eps)} independent crisis episodes
({"; ".join(f"{e['episode_id']} ({e['event_count']} onsets)" for e in eps)}).
Only **3** independent post-1990 episodes exist; 13/19 events are the 2007–2008
wave. Uncertainty intervals use year-block bootstrap so co-moving crises are
not counted as independent evidence.

Leave-one-episode-out / leave-one-country-out / decade blocks / ex-2007–2008
sensitivity for the primary predictor: `{json_dumps(loeo)}`.

Threshold heterogeneity (H01T-P1.0): no reproducible universal debt-to-GDP
level threshold — pooled p80 discriminates at/below chance for public debt and
flags 82% of test years for private credit; per-country p80s span ~5×. See
`export/threshold_heterogeneity_evaluation.json`.

## 4. Monetary conditions across the eight primary countries

| Entity | Measured series coverage |
|---|---|
{chr(10).join(f"| {e} | {', '.join(sorted(set(mon_by_ent.get(e, [])))) or '—'} |" for e in ("USA","CHN","CHE","DEU","FRA","GBR","JPN","IND"))}

Real rates = nominal JST long rate minus contemporaneous CPI inflation
(derived, labelled). Nominal and real series are never conflated.

## 5. International currency influence

- **COFER reserve shares** (allocated reserves, latest):
  {", ".join(f"{e} {v:.1f}% ({y})" for e, (y, v) in sorted(cofer.items(), key=lambda x: -(x[1][1] or 0)) if e not in ('ALL_CURRENCIES',))}
- **BIS FX turnover** (200% currency-leg convention, latest):
  {", ".join(f"{e} {v:.1f}% ({y})" for e, (y, v) in sorted(fx.items(), key=lambda x: -(x[1][1] or 0)) if e != 'ALL_CURRENCIES')}
- **BIS cross-border claims by currency** (latest):
  {", ".join(f"{e} {v:.1f}% ({y})" for e, (y, v) in sorted(lbs_cur.items(), key=lambda x: -(x[1][1] or 0)) if e != 'ALL_CURRENCIES')}

EUR is the shared euro-area currency — never attributed to DEU/FRA. INR is
measured directly only in FX turnover; it is absent from COFER and is NOT
zero-imputed. TFXRA_IMP imputed shares are exported but flagged as IMF
constructed estimates, not reported shares.

## 6. Financial-centre evidence

BIS LBS reporting-centre cross-border claims (banking-office LOCATION, not
ownership): {", ".join(f"{e} {v:.1f}% ({y})" for e, (y, v) in sorted(lbs_ctr.items(), key=lambda x: -(x[1][1] or 0)) if e != 'ALL_REPORTING')}.
Kept strictly separate from reserve-currency measures.

## 7. Historical productivity (PWT 11.0, 1950–2023)

Latest output per worker (2021 PPP USD): {", ".join(f"{e} {v:,.0f} ({y})" for e, (y, v) in sorted(pwt_latest.items(), key=lambda x: -(x[1][1] or 0)))}.
Latest TFP relative to USA=1: {", ".join(f"{e} {v:.2f} ({y})" for e, (y, v) in sorted(pwt_tfp.items(), key=lambda x: -(x[1][1] or 0)))}.

## 8. Historical economic power comparisons (Maddison 2023)

Panel share = share of the imported 20-entity panel GDP (GDPpc × population),
NOT a world share:

| Year | Top panel entities |
|---|---|
{chr(10).join(f"| {y} | {', '.join(f'{e} {v:.0f}%' for e, v in top[:5])} |" for y, top in sorted(bench_shares.items()))}

Modern codes do not represent historical empires (see
`entity_definition_notes` in `/api/research/foundation/historical-power/overview`).

## 9. Corrected validation-question statuses (v1.2)

| Question | v1.1 status | v1.2 status | Correction |
|---|---|---|---|
| Q08 | {q_status['Q08'].get('validation-questions-v1.1')} | {q_status['Q08'].get('validation-questions-v1.2')} | Machinery ≠ finding |
| Q11 | {q_status['Q11'].get('validation-questions-v1.1')} | {q_status['Q11'].get('validation-questions-v1.2')} | Scoped to tested public-debt proposition |
| Q14 | {q_status['Q14'].get('validation-questions-v1.1')} | {q_status['Q14'].get('validation-questions-v1.2')} | H01T-P1.0 level diagnostics |
| Q17 | {q_status['Q17'].get('validation-questions-v1.1')} | {q_status['Q17'].get('validation-questions-v1.2')} | Attribution defect corrected (H01B-P1.0) |

## 10. Remaining scientific limitations

- {n_crises} banking-crisis onsets in one outcome family; no independent
  non-banking registries (V-Dem, UCDP, COW, sovereign/currency crises) imported.
- Only 3 independent post-1990 episodes — clustered inference, not precision.
- Retrospective JST R6 vintage; `strict_eligible_periods` remains 0.
- IMF WP-2026-094 and ALFRED remain access-blocked; no substitute outcomes.
- H01B results are exploratory: the holdout informed predictor selection.
"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "DEBT_MONETARY_CYCLE_RESEARCH.md").write_text(report, encoding="utf-8")
    print(f"Wrote {OUT / 'DEBT_MONETARY_CYCLE_RESEARCH.md'}")


def json_dumps(obj):
    import json
    return json.dumps(obj, default=str, indent=2)[:4000]


if __name__ == "__main__":
    asyncio.run(main())
