from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cycle.force_definitions import FORCE_DEFINITIONS
from app.cycle.normalization_definitions import (
    CURRENT_MODEL_VERSION,
    ScoringPeriod,
)
from app.db.session import get_sessionmaker
from app.models import (
    Country,
    DataSource,
    Indicator,
    IndicatorRevision,
    IngestionRun,
    IngestionRunStatus,
    MarketInstrument,
    MarketObservation,
    Observation,
)
from app.research import service as research_service
from app.research.composite import COMPOSITE_MODELS
from app.research.forecast import (
    ForecastHorizon,
    TransitionRecord,
    evaluate_readiness,
)
from app.services import force_signal_service
from app.services.update_lock import update_lock, update_lock_status

ZURICH_TZ = ZoneInfo("Europe/Zurich")
REPO_ROOT = Path(__file__).resolve().parents[4]
_FORCE_NAMES = {d.code: d.name for d in FORCE_DEFINITIONS}

CURRENCY_ROLES: dict[str, dict[str, str]] = {
    "USA": {
        "currency_code": "USD",
        "role": "Primary global invoicing & FX anchor in Atlas market layer",
    },
    "CHN": {
        "currency_code": "CNY",
        "role": "Managed bilateral trade & settlement currency",
    },
    "DEU": {
        "currency_code": "EUR",
        "role": "Eurozone shared reserve & trade currency",
    },
    "FRA": {
        "currency_code": "EUR",
        "role": "Eurozone shared reserve & trade currency",
    },
    "GBR": {
        "currency_code": "GBP",
        "role": "Secondary international financial-centre currency",
    },
    "JPN": {
        "currency_code": "JPY",
        "role": "Major funding & reserve currency",
    },
    "CHE": {
        "currency_code": "CHF",
        "role": "Safe-haven regional financial currency",
    },
    "IND": {
        "currency_code": "INR",
        "role": "Domestic-led emerging power currency",
    },
}

POWER_INDICATORS = (
    "GDP_CURRENT_USD",
    "GDP_PER_CAPITA",
    "GDP_GROWTH",
    "MILITARY_EXPENDITURE_USD",
    "MILITARY_EXPENDITURE_GDP",
    "EXPORTS_GDP",
    "IMPORTS_GDP",
    "CURRENT_ACCOUNT_GDP",
    "RND_EXPENDITURE_GDP",
    "LABOUR_PRODUCTIVITY_PER_HOUR",
    "GOVERNMENT_DEBT_GDP",
    "POPULATION",
    "REER_INDEX",
    "RULE_OF_LAW_WGI_SCORE",
    "TERTIARY_ATTAINMENT_25_34",
)

_MEM_CACHE: dict[tuple[str, str, int], dict[str, Any]] = {}
_REFRESH_LOCK = asyncio.Lock()
_REFRESH_JOB: dict[str, Any] = {
    "running": False,
    "mode": None,
    "started_at": None,
    "completed_at": None,
    "current_provider": None,
    "completed_steps": 0,
    "total_steps": 0,
    "inserted": 0,
    "revised": 0,
    "failed": 0,
    "status": "idle",
    "error": None,
}


def observatory_dir() -> Path:
    override = os.environ.get("BCA_OBSERVATORY_DIR")
    p = Path(override) if override else (REPO_ROOT / ".run" / "observatory")
    p.mkdir(parents=True, exist_ok=True)
    return p


def latest_completed_scoring_period() -> ScoringPeriod:
    today = datetime.now(timezone.utc).date()
    quarter = (today.month - 1) // 3
    if quarter == 0:
        return ScoringPeriod(today.year - 1, 4)
    return ScoringPeriod(today.year, quarter)


def to_utc_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def to_zurich_display(dt_or_iso: datetime | str | None) -> str | None:
    if dt_or_iso is None:
        return None
    if isinstance(dt_or_iso, str):
        dt = datetime.fromisoformat(dt_or_iso.replace("Z", "+00:00"))
    else:
        dt = dt_or_iso
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(ZURICH_TZ).strftime("%Y-%m-%d %H:%M %Z")


async def db_fingerprint(session: AsyncSession) -> str:
    obs_row = (
        await session.execute(
            select(func.count(Observation.id), func.max(Observation.id))
        )
    ).one()
    rev_row = (
        await session.execute(
            select(
                func.count(IndicatorRevision.id),
                func.max(IndicatorRevision.id),
            )
        )
    ).one()
    cnt_countries = (
        await session.execute(select(func.count(Country.id)))
    ).scalar() or 0
    url_tag = hashlib.sha1(
        str(getattr(session.bind, "url", "mem")).encode("utf-8")
    ).hexdigest()[:10]
    sp = latest_completed_scoring_period()
    return (
        f"{url_tag}:c{cnt_countries}:o{obs_row[0]}-{obs_row[1] or 0}:"
        f"r{rev_row[0]}-{rev_row[1] or 0}:{sp.year}-Q{sp.quarter}"
    )


async def _latest_indicator_series(
    session: AsyncSession,
    country_ids: dict[str, int],
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Fetch latest-vintage observation series for POWER_INDICATORS across countries."""
    rows = (
        await session.execute(
            select(
                Country.iso3,
                Indicator.code,
                Observation.value,
                Observation.period_start,
                Observation.observation_date,
                Observation.vintage_number,
                DataSource.name,
                DataSource.key,
            )
            .join(Country, Country.id == Observation.country_id)
            .join(Indicator, Indicator.id == Observation.indicator_id)
            .join(DataSource, DataSource.id == Observation.data_source_id)
            .where(
                Indicator.code.in_(POWER_INDICATORS),
                Observation.country_id.in_(list(country_ids.values())),
            )
            .order_by(
                Country.iso3,
                Indicator.code,
                Observation.observation_date.asc(),
                Observation.vintage_number.asc(),
            )
        )
    ).all()

    # Keep highest vintage per (iso3, code, year)
    by_year: dict[tuple[str, str, int], dict[str, Any]] = {}
    for iso3, code, val, p_start, obs_date, vintage, src_name, src_key in rows:
        dt = p_start or obs_date
        if dt is None or val is None:
            continue
        yr = dt.year
        key = (iso3, code, yr)
        prev = by_year.get(key)
        if prev is None or vintage >= prev["vintage"]:
            by_year[key] = {
                "year": yr,
                "period": str(yr),
                "value": float(val),
                "vintage": int(vintage or 1),
                "source": src_name or src_key,
                "source_key": src_key,
            }

    out: dict[str, dict[str, list[dict[str, Any]]]] = {
        iso3: {} for iso3 in country_ids
    }
    for (iso3, code, _yr), entry in sorted(by_year.items()):
        out.setdefault(iso3, {}).setdefault(code, []).append(entry)
    return out


async def _latest_yields(session: AsyncSession) -> dict[str, dict[str, Any]]:
    rows = (
        await session.execute(
            select(
                Country.iso3,
                MarketInstrument.code,
                MarketObservation.value,
                MarketObservation.obs_date,
            )
            .join(
                MarketInstrument,
                MarketInstrument.id == MarketObservation.instrument_id,
            )
            .join(Country, Country.id == MarketInstrument.country_id)
            .where(MarketInstrument.asset_class == "gov_bond_yield")
            .order_by(MarketObservation.obs_date.asc())
        )
    ).all()
    latest: dict[str, dict[str, Any]] = {}
    for iso3, code, val, obs_date in rows:
        if iso3 and val is not None:
            latest[iso3] = {
                "instrument_code": code,
                "value": float(val),
                "period": obs_date.isoformat() if obs_date else None,
                "source": "FRED / OECD",
            }
    return latest


def _latest_point(
    series: dict[str, list[dict[str, Any]]], code: str
) -> dict[str, Any] | None:
    pts = series.get(code)
    return pts[-1] if pts else None


def _point_near_offset(
    series: dict[str, list[dict[str, Any]]], code: str, years_back: int = 5
) -> dict[str, Any] | None:
    pts = series.get(code)
    if not pts or len(pts) < 2:
        return None
    target_yr = pts[-1]["year"] - years_back
    candidates = [p for p in pts[:-1] if p["year"] <= target_yr]
    return candidates[-1] if candidates else pts[0]


async def _compute_country_block(
    session: AsyncSession,
    iso3: str,
    name: str,
    region: str | None,
    model_id: str,
    start_year: int,
    latest_sp: ScoringPeriod,
) -> dict[str, Any]:
    cycle = await research_service.cycle_history(
        session, iso3, model_id, start_year, latest_sp.year, latest_sp
    )
    signals = await force_signal_service.build_force_signals_as_of(
        session, iso3, latest_sp
    )
    forces_list: list[dict[str, Any]] = []
    scored_count = 0
    dim_only_count = 0
    context_count = 0
    for s in signals:
        if s.level_score is not None:
            exec_status = "scored"
            scored_count += 1
        elif s.relative_score is not None or s.momentum is not None:
            exec_status = "dimension_only"
            dim_only_count += 1
        else:
            exec_status = "context_only"
            context_count += 1
        forces_list.append(
            {
                "force_code": s.force_code,
                "force_name": _FORCE_NAMES.get(s.force_code, s.force_code),
                "execution_status": exec_status,
                "level_score": s.level_score,
                "relative_score": s.relative_score,
                "momentum_score": s.momentum,
                "coverage_status": s.coverage_status.value,
                "period": s.scoring_period,
            }
        )

    scored_sorted = sorted(
        [f for f in forces_list if f["level_score"] is not None],
        key=lambda x: float(x["level_score"]),
        reverse=True,
    )
    history_pts = [
        {
            "period": p.period,
            "score": p.score,
            "momentum": p.momentum,
            "stage": p.stage.value if p.stage else None,
            "phase": p.phase.value if p.phase else None,
            "reason": p.reason,
        }
        for p in cycle.points
    ]
    last_pt = history_pts[-1] if history_pts else None
    genuine_transitions = [
        t for t in cycle.transitions if t.get("reason") != "initial"
    ]
    mom = last_pt["momentum"] if last_pt else None
    stage = last_pt["stage"] if last_pt else None
    if stage is None:
        direction = "unclassified"
    elif mom is not None and mom > 1.0:
        direction = "rising"
    elif mom is not None and mom < -1.0:
        direction = "declining"
    else:
        direction = "steady"

    return {
        "iso3": iso3,
        "name": name,
        "region": region,
        "stage": stage,
        "phase": last_pt["phase"] if last_pt else None,
        "domestic_condition_score": last_pt["score"] if last_pt else None,
        "score": last_pt["score"] if last_pt else None,
        "momentum": mom,
        "coverage_ratio": cycle.coverage_ratio,
        "period": last_pt["period"] if last_pt else f"{latest_sp.year}-Q4",
        "direction": direction,
        "classified": stage is not None,
        "recent_transition": (
            genuine_transitions[-1] if genuine_transitions else None
        ),
        "transitions": list(cycle.transitions),
        "history": history_pts,
        "force_summary": {
            "scored_count": scored_count,
            "dimension_only_count": dim_only_count,
            "context_only_count": context_count,
            "top_forces": scored_sorted[:3],
            "weakest_forces": list(reversed(scored_sorted[-3:]))
            if len(scored_sorted) >= 3
            else list(reversed(scored_sorted)),
            "forces": forces_list,
        },
    }


async def compute_core_observatory(
    session: AsyncSession,
    model_id: str = "model_b_domain",
    start_year: int = 2000,
) -> dict[str, Any]:
    if model_id not in COMPOSITE_MODELS:
        raise KeyError(model_id)

    fp = await db_fingerprint(session)
    cache_key = (fp, model_id, start_year)
    if cache_key in _MEM_CACHE:
        return _MEM_CACHE[cache_key]

    disk_cache = (
        observatory_dir()
        / f"core_cache_{model_id}_{start_year}.json"
    )
    if disk_cache.exists():
        try:
            saved = json.loads(disk_cache.read_text(encoding="utf-8"))
            if saved.get("db_fingerprint") == fp:
                _MEM_CACHE[cache_key] = saved
                return saved
        except Exception:
            pass

    country_rows = (
        (await session.execute(select(Country).order_by(Country.iso3)))
        .scalars()
        .all()
    )
    country_ids = {c.iso3: c.id for c in country_rows}
    latest_sp = latest_completed_scoring_period()
    ind_series = await _latest_indicator_series(session, country_ids)
    yields_by_iso = await _latest_yields(session)

    dialect = getattr(getattr(session, "bind", None), "dialect", None)
    is_sqlite = getattr(dialect, "name", "") == "sqlite"

    if is_sqlite:
        blocks = [
            await _compute_country_block(
                session,
                c.iso3,
                c.name,
                getattr(c, "region", None),
                model_id,
                start_year,
                latest_sp,
            )
            for c in country_rows
        ]
    else:
        sm = get_sessionmaker()

        async def _run_one(c: Country) -> dict[str, Any]:
            async with sm() as s:
                return await _compute_country_block(
                    s,
                    c.iso3,
                    c.name,
                    getattr(c, "region", None),
                    model_id,
                    start_year,
                    latest_sp,
                )

        blocks = list(
            await asyncio.gather(*[_run_one(c) for c in country_rows])
        )

    # International power metrics — strictly empirical, never conflated with domestic condition
    gdp_totals = sum(
        (_latest_point(ind_series.get(b["iso3"], {}), "GDP_CURRENT_USD") or {}).get(
            "value", 0.0
        )
        for b in blocks
    )
    mil_totals = sum(
        (
            _latest_point(
                ind_series.get(b["iso3"], {}), "MILITARY_EXPENDITURE_USD"
            )
            or {}
        ).get("value", 0.0)
        for b in blocks
    )

    trade_usd_by_iso: dict[str, dict[str, Any] | None] = {}
    rnd_usd_by_iso: dict[str, dict[str, Any] | None] = {}
    for b in blocks:
        iso3 = b["iso3"]
        cs = ind_series.get(iso3, {})
        gdp = _latest_point(cs, "GDP_CURRENT_USD")
        exp = _latest_point(cs, "EXPORTS_GDP")
        imp = _latest_point(cs, "IMPORTS_GDP")
        rnd = _latest_point(cs, "RND_EXPENDITURE_GDP")
        if (
            gdp
            and exp
            and imp
            and abs(exp["year"] - imp["year"]) <= 1
            and abs(gdp["year"] - exp["year"]) <= 1
        ):
            vol = gdp["value"] * (exp["value"] + imp["value"]) / 100.0
            trade_usd_by_iso[iso3] = {
                "value": vol,
                "period": str(min(gdp["year"], exp["year"], imp["year"])),
                "source": f"{exp['source']} + {gdp['source']}",
            }
        else:
            trade_usd_by_iso[iso3] = None

        if gdp and rnd and abs(gdp["year"] - rnd["year"]) <= 2:
            rnd_usd_by_iso[iso3] = {
                "value": gdp["value"] * rnd["value"] / 100.0,
                "period": str(min(gdp["year"], rnd["year"])),
                "source": f"{rnd['source']} + {gdp['source']}",
            }
        else:
            rnd_usd_by_iso[iso3] = None

    trade_totals = sum(
        (v or {}).get("value", 0.0) for v in trade_usd_by_iso.values()
    )
    rnd_totals = sum(
        (v or {}).get("value", 0.0) for v in rnd_usd_by_iso.values()
    )

    for b in blocks:
        iso3 = b["iso3"]
        cs = ind_series.get(iso3, {})
        gdp = _latest_point(cs, "GDP_CURRENT_USD")
        mil_usd = _latest_point(cs, "MILITARY_EXPENDITURE_USD")
        mil_gdp = _latest_point(cs, "MILITARY_EXPENDITURE_GDP")
        exp = _latest_point(cs, "EXPORTS_GDP")
        imp = _latest_point(cs, "IMPORTS_GDP")
        ca = _latest_point(cs, "CURRENT_ACCOUNT_GDP")
        rnd = _latest_point(cs, "RND_EXPENDITURE_GDP")
        reer = _latest_point(cs, "REER_INDEX")
        mil_force = next(
            (
                f
                for f in b["force_summary"]["forces"]
                if f["force_code"] == "military_strength"
            ),
            None,
        )
        ccy_meta = CURRENCY_ROLES.get(
            iso3,
            {"currency_code": "N/A", "role": "National currency"},
        )
        tr_vol = trade_usd_by_iso.get(iso3)
        rnd_vol = rnd_usd_by_iso.get(iso3)
        yld = yields_by_iso.get(iso3)

        b["international_power"] = {
            "economic_size": {
                "indicator_code": "GDP_CURRENT_USD",
                "value_usd": gdp["value"] if gdp else None,
                "tracked_share_pct": (
                    round(gdp["value"] / gdp_totals * 100.0, 2)
                    if gdp and gdp_totals > 0
                    else None
                ),
                "period": gdp["period"] if gdp else None,
                "source": gdp["source"] if gdp else None,
            },
            "military_resources": {
                "indicator_code": "MILITARY_EXPENDITURE_USD",
                "expenditure_usd": mil_usd["value"] if mil_usd else None,
                "tracked_share_pct": (
                    round(mil_usd["value"] / mil_totals * 100.0, 2)
                    if mil_usd and mil_totals > 0
                    else None
                ),
                "pct_gdp": mil_gdp["value"] if mil_gdp else None,
                "relative_score": (
                    mil_force["relative_score"] if mil_force else None
                ),
                "period": mil_usd["period"] if mil_usd else None,
                "source": mil_usd["source"] if mil_usd else None,
            },
            "international_trade": {
                "trade_volume_usd": tr_vol["value"] if tr_vol else None,
                "tracked_share_pct": (
                    round(tr_vol["value"] / trade_totals * 100.0, 2)
                    if tr_vol and trade_totals > 0
                    else None
                ),
                "exports_pct_gdp": exp["value"] if exp else None,
                "imports_pct_gdp": imp["value"] if imp else None,
                "current_account_pct_gdp": ca["value"] if ca else None,
                "period": (
                    tr_vol["period"]
                    if tr_vol
                    else (exp["period"] if exp else None)
                ),
                "source": (
                    tr_vol["source"]
                    if tr_vol
                    else (exp["source"] if exp else None)
                ),
            },
            "innovation_scale": {
                "rnd_pct_gdp": rnd["value"] if rnd else None,
                "implied_rnd_usd": rnd_vol["value"] if rnd_vol else None,
                "tracked_share_pct": (
                    round(rnd_vol["value"] / rnd_totals * 100.0, 2)
                    if rnd_vol and rnd_totals > 0
                    else None
                ),
                "period": rnd["period"] if rnd else None,
                "source": rnd["source"] if rnd else None,
            },
            "monetary_influence": {
                "currency_code": ccy_meta["currency_code"],
                "reserve_anchor_role": ccy_meta["role"],
                "reer_index": reer["value"] if reer else None,
                "reer_period": reer["period"] if reer else None,
                "gov_10y_yield": yld["value"] if yld else None,
                "gov_10y_period": yld["period"] if yld else None,
                "source": reer["source"] if reer else (yld["source"] if yld else None),
                "scope_note": (
                    "IMF COFER reserve-share series is not yet ingested; "
                    "monetary influence reports currency role alongside BIS REER "
                    "and sovereign 10Y yield data."
                ),
            },
        }
        b["indicator_snapshots"] = {
            code: {
                "latest": _latest_point(cs, code),
                "prior_5y": _point_near_offset(cs, code, 5),
            }
            for code in POWER_INDICATORS
        }

    # Explicit separated rankings (§13)
    by_gdp = sorted(
        [
            b
            for b in blocks
            if b["international_power"]["economic_size"]["value_usd"] is not None
        ],
        key=lambda x: float(
            x["international_power"]["economic_size"]["value_usd"]
        ),
        reverse=True,
    )
    gdp_rank = {b["iso3"]: i + 1 for i, b in enumerate(by_gdp)}

    by_cond = sorted(
        [b for b in blocks if b["domestic_condition_score"] is not None],
        key=lambda x: float(x["domestic_condition_score"]),
        reverse=True,
    )
    cond_rank = {b["iso3"]: i + 1 for i, b in enumerate(by_cond)}

    for b in blocks:
        b["international_power"]["tracked_gdp_rank"] = gdp_rank.get(b["iso3"])
        b["domestic_condition_rank"] = cond_rank.get(b["iso3"])

    all_periods = sorted(
        {pt["period"] for b in blocks for pt in b["history"]}
    )

    payload = {
        "db_fingerprint": fp,
        "computed_at": to_utc_iso(datetime.now(timezone.utc)),
        "methodology_status": "experimental",
        "normalization_version": CURRENT_MODEL_VERSION.version_id,
        "model": {
            "model_id": model_id,
            "model_version": COMPOSITE_MODELS[model_id].version,
            "available_models": [
                {
                    "model_id": mid,
                    "model_version": m.version,
                    "kind": m.kind,
                    "notes": m.notes,
                }
                for mid, m in COMPOSITE_MODELS.items()
            ],
        },
        "scoring_period": f"{latest_sp.year}-Q{latest_sp.quarter}",
        "available_periods": all_periods,
        "countries": blocks,
        "power_summary": {
            "largest_economy_iso3": by_gdp[0]["iso3"] if by_gdp else None,
            "second_economy_iso3": (
                by_gdp[1]["iso3"] if len(by_gdp) > 1 else None
            ),
            "highest_domestic_condition_iso3": (
                by_cond[0]["iso3"] if by_cond else None
            ),
            "separation_note": (
                "Domestic economic & institutional condition (experimental 0–100 "
                "composite) measures internal governance, education, productivity "
                "and social cohesion — a small economy such as Switzerland can "
                "lead on domestic conditions without holding international empire "
                "scale. International power is reported separately through GDP "
                "scale, military expenditure, trade volume and monetary role."
            ),
        },
    }

    _MEM_CACHE[cache_key] = payload
    if not is_sqlite:
        try:
            disk_cache.write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
        except Exception:
            pass
    return payload


def build_transition_monitor(
    core: dict[str, Any],
    incumbent_iso3: str = "USA",
    challenger_iso3: str = "CHN",
    strict_eligible_periods: int = 0,
) -> dict[str, Any]:
    by_iso = {c["iso3"]: c for c in core["countries"]}
    inc = by_iso.get(incumbent_iso3.upper()) or (
        core["countries"][0] if core["countries"] else None
    )
    chal = by_iso.get(challenger_iso3.upper()) or (
        core["countries"][1]
        if len(core["countries"]) > 1
        else inc
    )

    if inc is None or chal is None:
        return {
            "incumbent_iso3": incumbent_iso3,
            "challenger_iso3": challenger_iso3,
            "measurements": [],
            "areas_of_convergence": [],
            "areas_of_divergence": [],
            "historical_evidence": {},
            "forecast_readiness": {
                "overall_available": False,
                "estimated_transition_window": "Not estimable",
                "blockers": ["insufficient_country_data"],
                "horizons": [],
            },
        }

    def _snap_pair(code: str) -> tuple[dict | None, dict | None, dict | None, dict | None]:
        inc_s = inc.get("indicator_snapshots", {}).get(code, {})
        chal_s = chal.get("indicator_snapshots", {}).get(code, {})
        return (
            inc_s.get("latest"),
            inc_s.get("prior_5y"),
            chal_s.get("latest"),
            chal_s.get("prior_5y"),
        )

    specs = [
        ("GDP_CURRENT_USD", "Economic output (GDP)", "scale", "USD", "ratio"),
        (
            "MILITARY_EXPENDITURE_USD",
            "Military expenditure",
            "military",
            "USD",
            "ratio",
        ),
        ("EXPORTS_GDP", "Exports (% of GDP)", "trade", "% GDP", "diff"),
        (
            "RND_EXPENDITURE_GDP",
            "R&D intensity (% of GDP)",
            "innovation",
            "% GDP",
            "diff",
        ),
        ("GDP_PER_CAPITA", "GDP per capita", "prosperity", "USD", "ratio"),
        (
            "LABOUR_PRODUCTIVITY_PER_HOUR",
            "Labour productivity",
            "productivity",
            "PPP $/hr",
            "ratio",
        ),
        (
            "RULE_OF_LAW_WGI_SCORE",
            "Rule of law (WGI)",
            "institutions",
            "score 0-100",
            "diff",
        ),
        (
            "TERTIARY_ATTAINMENT_25_34",
            "Tertiary education (25–34)",
            "education",
            "%",
            "diff",
        ),
        (
            "GOVERNMENT_DEBT_GDP",
            "Government debt (% of GDP)",
            "debt",
            "% GDP",
            "diff",
        ),
    ]

    measurements: list[dict[str, Any]] = []
    convergences: list[dict[str, Any]] = []
    divergences: list[dict[str, Any]] = []

    for code, label, category, unit, mode in specs:
        i_now, i_prev, c_now, c_prev = _snap_pair(code)
        iv = i_now["value"] if i_now else None
        cv = c_now["value"] if c_now else None
        ratio = (
            round(cv / iv, 4)
            if (iv is not None and cv is not None and iv > 0)
            else None
        )
        gap_now = (
            abs(iv - cv) if (iv is not None and cv is not None) else None
        )
        relationship = "insufficient_data"
        trend_note = None
        if i_now and i_prev and c_now and c_prev:
            if mode == "ratio" and i_now["value"] > 0 and i_prev["value"] > 0:
                r_prev = c_prev["value"] / i_prev["value"]
                r_now = c_now["value"] / i_now["value"]
                gap_prev_rel = abs(1.0 - r_prev)
                gap_now_rel = abs(1.0 - r_now)
                if gap_now_rel < gap_prev_rel - 0.02:
                    relationship = "convergence"
                    trend_note = (
                        f"Challenger/incumbent ratio moved from "
                        f"{r_prev * 100:.1f}% to {r_now * 100:.1f}%"
                    )
                elif gap_now_rel > gap_prev_rel + 0.02:
                    relationship = "divergence"
                    trend_note = (
                        f"Relative gap widened ({r_prev * 100:.1f}% -> "
                        f"{r_now * 100:.1f}%)"
                    )
                else:
                    relationship = "stable"
            else:
                g_prev = abs(i_prev["value"] - c_prev["value"])
                g_now = abs(i_now["value"] - c_now["value"])
                if g_now < g_prev - 0.5:
                    relationship = "convergence"
                    trend_note = (
                        f"Spread narrowed from {g_prev:.1f} to {g_now:.1f} {unit}"
                    )
                elif g_now > g_prev + 0.5:
                    relationship = "divergence"
                    trend_note = (
                        f"Spread widened from {g_prev:.1f} to {g_now:.1f} {unit}"
                    )
                else:
                    relationship = "stable"

        row = {
            "key": code,
            "label": label,
            "category": category,
            "unit": unit,
            "incumbent_value": iv,
            "challenger_value": cv,
            "challenger_to_incumbent_ratio": ratio,
            "absolute_gap": gap_now,
            "relationship": relationship,
            "trend_note": trend_note,
            "period": (
                i_now["period"]
                if i_now
                else (c_now["period"] if c_now else None)
            ),
            "source": (
                i_now["source"]
                if i_now
                else (c_now["source"] if c_now else None)
            ),
        }
        measurements.append(row)
        if relationship == "convergence":
            convergences.append(row)
        elif relationship == "divergence":
            divergences.append(row)

    # Also compare experimental domestic condition composite trajectory
    inc_hist = [p for p in inc["history"] if p["score"] is not None]
    chal_hist = [p for p in chal["history"] if p["score"] is not None]
    comp_rel = "insufficient_data"
    comp_note = None
    if len(inc_hist) >= 6 and len(chal_hist) >= 6:
        g_prev = abs(inc_hist[-6]["score"] - chal_hist[-6]["score"])
        g_now = abs(inc_hist[-1]["score"] - chal_hist[-1]["score"])
        if g_now < g_prev - 1.0:
            comp_rel = "convergence"
            comp_note = (
                f"Composite gap narrowed from {g_prev:.1f} to {g_now:.1f} pts"
            )
        elif g_now > g_prev + 1.0:
            comp_rel = "divergence"
            comp_note = (
                f"Composite gap widened from {g_prev:.1f} to {g_now:.1f} pts"
            )
        else:
            comp_rel = "stable"
    comp_row = {
        "key": "DOMESTIC_CONDITION_COMPOSITE",
        "label": "Domestic condition composite (experimental)",
        "category": "cycle_composite",
        "unit": "score 0-100",
        "incumbent_value": inc["domestic_condition_score"],
        "challenger_value": chal["domestic_condition_score"],
        "challenger_to_incumbent_ratio": (
            round(
                chal["domestic_condition_score"]
                / inc["domestic_condition_score"],
                4,
            )
            if inc["domestic_condition_score"]
            and chal["domestic_condition_score"]
            else None
        ),
        "absolute_gap": (
            abs(
                inc["domestic_condition_score"]
                - chal["domestic_condition_score"]
            )
            if inc["domestic_condition_score"] is not None
            and chal["domestic_condition_score"] is not None
            else None
        ),
        "relationship": comp_rel,
        "trend_note": comp_note,
        "period": inc["period"],
        "source": f"Atlas {core['model']['model_id']} ({core['model']['model_version']})",
    }
    measurements.insert(0, comp_row)
    if comp_rel == "convergence":
        convergences.insert(0, comp_row)
    elif comp_rel == "divergence":
        divergences.insert(0, comp_row)

    # Forecast readiness across 1y, 2y, 5y, 10y using real evaluate_readiness
    model_id = core["model"]["model_id"]
    model_ver = core["model"]["model_version"]
    scored_periods = sorted(
        {
            p["period"]
            for c in core["countries"]
            for p in c["history"]
            if p["score"] is not None
        }
    )
    transitions: list[TransitionRecord] = []
    for c in core["countries"]:
        for t in c.get("transitions", []):
            if t.get("reason") == "initial" or "from" not in t:
                continue
            transitions.append(
                TransitionRecord(
                    country_iso3=c["iso3"],
                    period=t["period"],
                    from_stage=t["from"],
                    to_stage=t["to"],
                    model_id=model_id,
                )
            )
    report = evaluate_readiness(
        model_id=model_id,
        model_version=model_ver,
        scored_periods=scored_periods,
        transitions=transitions,
        strict_eligible_periods=strict_eligible_periods,
    )

    horizons_out = [
        {
            "horizon": hr.horizon.value,
            "horizon_label": {
                ForecastHorizon.one_year: "1 year",
                ForecastHorizon.two_years: "2 years",
                ForecastHorizon.five_years: "5 years",
                ForecastHorizon.ten_years: "10 years",
            }[hr.horizon],
            "horizon_quarters": hr.horizon_quarters,
            "available": hr.available,
            "status_label": (
                "Supported" if hr.available else "Gated — insufficient evidence"
            ),
            "unavailable_reason": hr.unavailable_reason,
            "eligible_samples": hr.eligible_samples,
            "positive_transitions": hr.positive_transitions,
            "gates": [
                {
                    "gate": g.gate,
                    "passed": g.passed,
                    "value": g.value,
                    "requirement": g.requirement,
                    "note": g.note or None,
                }
                for g in hr.gates
            ],
        }
        for hr in report.horizon_results
    ]

    return {
        "incumbent_iso3": inc["iso3"],
        "incumbent_name": inc["name"],
        "incumbent_stage": inc["stage"],
        "incumbent_direction": inc["direction"],
        "challenger_iso3": chal["iso3"],
        "challenger_name": chal["name"],
        "challenger_stage": chal["stage"],
        "challenger_direction": chal["direction"],
        "measurements": measurements,
        "areas_of_convergence": convergences,
        "areas_of_divergence": divergences,
        "historical_evidence": {
            "incumbent_transitions": [
                t
                for t in inc.get("transitions", [])
                if t.get("reason") != "initial"
            ],
            "challenger_transitions": [
                t
                for t in chal.get("transitions", [])
                if t.get("reason") != "initial"
            ],
            "shared_scored_periods": len(
                {p["period"] for p in inc_hist}
                & {p["period"] for p in chal_hist}
            ),
            "total_dataset_transitions": len(transitions),
        },
        "forecast_readiness": {
            "methodology_status": "experimental",
            "overall_available": report.overall_available,
            "estimated_transition_window": (
                "Supported — inspect horizon probabilities"
                if report.overall_available
                else "Not estimable"
            ),
            "blockers": list(report.blockers),
            "total_scored_periods": report.total_scored_periods,
            "total_genuine_transitions": report.total_genuine_transitions,
            "strict_eligible_periods": report.strict_eligible_periods,
            "horizons": horizons_out,
        },
    }


def extract_snapshot_record(core: dict[str, Any]) -> dict[str, Any]:
    """Compact deterministic snapshot of calculated state for diffing."""
    countries_snap: dict[str, Any] = {}
    for c in core["countries"]:
        forces_snap = {
            f["force_code"]: {
                "force_name": f["force_name"],
                "level_score": f["level_score"],
                "relative_score": f["relative_score"],
                "momentum_score": f["momentum_score"],
                "coverage_status": f["coverage_status"],
                "period": f["period"],
            }
            for f in c["force_summary"]["forces"]
        }
        ip = c["international_power"]
        countries_snap[c["iso3"]] = {
            "name": c["name"],
            "stage": c["stage"],
            "phase": c["phase"],
            "domestic_condition_score": c["domestic_condition_score"],
            "momentum": c["momentum"],
            "coverage_ratio": c["coverage_ratio"],
            "period": c["period"],
            "forces": forces_snap,
            "power": {
                "gdp_share_pct": ip["economic_size"]["tracked_share_pct"],
                "gdp_period": ip["economic_size"]["period"],
                "gdp_source": ip["economic_size"]["source"],
                "military_share_pct": ip["military_resources"][
                    "tracked_share_pct"
                ],
                "military_period": ip["military_resources"]["period"],
                "military_source": ip["military_resources"]["source"],
                "trade_share_pct": ip["international_trade"][
                    "tracked_share_pct"
                ],
                "trade_period": ip["international_trade"]["period"],
                "trade_source": ip["international_trade"]["source"],
            },
        }
    return {
        "calculated_at": core["computed_at"],
        "db_fingerprint": core["db_fingerprint"],
        "model_id": core["model"]["model_id"],
        "scoring_period": core["scoring_period"],
        "countries": countries_snap,
    }


def diff_snapshots(
    prev: dict[str, Any] | None,
    curr: dict[str, Any],
    revisions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compare two calculation snapshots honestly (§12).

    Missing data (`curr_val is None`) is NEVER treated as economic deterioration.
    """
    if prev is None:
        return {
            "changed_classifications_count": 0,
            "changes": [],
            "summary_message": "No new economic changes detected.",
        }

    changes: list[dict[str, Any]] = []
    changed_countries: set[str] = set()
    prev_countries = prev.get("countries", {})
    curr_countries = curr.get("countries", {})
    model_src = f"Atlas {curr.get('model_id', 'model_b_domain')}"

    for iso3, c_curr in sorted(curr_countries.items()):
        c_prev = prev_countries.get(iso3)
        if not c_prev:
            continue
        cname = c_curr.get("name", iso3)
        period = c_curr.get("period")

        # 1. Country stage classification (never treat null as decline)
        st_prev = c_prev.get("stage")
        st_curr = c_curr.get("stage")
        if st_curr is not None and st_prev != st_curr:
            if st_prev is not None:
                changed_countries.add(iso3)
                changes.append(
                    {
                        "category": "classification",
                        "country_iso3": iso3,
                        "country_name": cname,
                        "measurement": "Experimental cycle stage",
                        "previous_value": st_prev,
                        "current_value": st_curr,
                        "difference": f"{st_prev} -> {st_curr}",
                        "observation_period": period,
                        "source": model_src,
                        "direction": "changed",
                    }
                )
            else:
                changes.append(
                    {
                        "category": "coverage",
                        "country_iso3": iso3,
                        "country_name": cname,
                        "measurement": "Experimental cycle stage coverage",
                        "previous_value": None,
                        "current_value": st_curr,
                        "difference": "newly classifiable",
                        "observation_period": period,
                        "source": model_src,
                        "direction": "coverage_added",
                    }
                )

        # 2. Composite momentum
        m_prev = c_prev.get("momentum")
        m_curr = c_curr.get("momentum")
        if (
            m_prev is not None
            and m_curr is not None
            and abs(float(m_curr) - float(m_prev)) > 0.05
        ):
            delta = round(float(m_curr) - float(m_prev), 3)
            changes.append(
                {
                    "category": "momentum",
                    "country_iso3": iso3,
                    "country_name": cname,
                    "measurement": "Composite cycle momentum",
                    "previous_value": round(float(m_prev), 3),
                    "current_value": round(float(m_curr), 3),
                    "difference": delta,
                    "observation_period": period,
                    "source": model_src,
                    "direction": "up" if delta > 0 else "down",
                }
            )

        # 3. Force levels & force momentum & coverage
        f_prev_map = c_prev.get("forces", {})
        for fcode, f_curr in c_curr.get("forces", {}).items():
            f_prev = f_prev_map.get(fcode, {})
            fname = f_curr.get("force_name", fcode)
            fperiod = f_curr.get("period") or period

            lv_prev = f_prev.get("level_score")
            lv_curr = f_curr.get("level_score")
            if lv_prev is None and lv_curr is not None:
                changes.append(
                    {
                        "category": "coverage",
                        "country_iso3": iso3,
                        "country_name": cname,
                        "measurement": f"{fname} (force level coverage)",
                        "previous_value": None,
                        "current_value": round(float(lv_curr), 2),
                        "difference": "newly available",
                        "observation_period": fperiod,
                        "source": "Atlas force engine",
                        "direction": "coverage_added",
                    }
                )
            elif (
                lv_prev is not None
                and lv_curr is not None
                and abs(float(lv_curr) - float(lv_prev)) > 0.05
            ):
                delta = round(float(lv_curr) - float(lv_prev), 2)
                changes.append(
                    {
                        "category": "force_level",
                        "country_iso3": iso3,
                        "country_name": cname,
                        "measurement": f"{fname} level",
                        "previous_value": round(float(lv_prev), 2),
                        "current_value": round(float(lv_curr), 2),
                        "difference": delta,
                        "observation_period": fperiod,
                        "source": "Atlas force engine",
                        "direction": "up" if delta > 0 else "down",
                    }
                )

            fm_prev = f_prev.get("momentum_score")
            fm_curr = f_curr.get("momentum_score")
            if (
                fm_prev is not None
                and fm_curr is not None
                and abs(float(fm_curr) - float(fm_prev)) > 0.05
            ):
                delta = round(float(fm_curr) - float(fm_prev), 2)
                changes.append(
                    {
                        "category": "momentum",
                        "country_iso3": iso3,
                        "country_name": cname,
                        "measurement": f"{fname} momentum",
                        "previous_value": round(float(fm_prev), 2),
                        "current_value": round(float(fm_curr), 2),
                        "difference": delta,
                        "observation_period": fperiod,
                        "source": "Atlas force engine",
                        "direction": "up" if delta > 0 else "down",
                    }
                )

        # 4. Relative international power shares
        p_prev = c_prev.get("power", {})
        p_curr = c_curr.get("power", {})
        for key, label, p_key, s_key in [
            ("gdp_share_pct", "Tracked GDP share (%)", "gdp_period", "gdp_source"),
            (
                "military_share_pct",
                "Tracked military expenditure share (%)",
                "military_period",
                "military_source",
            ),
            (
                "trade_share_pct",
                "Tracked trade volume share (%)",
                "trade_period",
                "trade_source",
            ),
        ]:
            v_prev = p_prev.get(key)
            v_curr = p_curr.get(key)
            if (
                v_prev is not None
                and v_curr is not None
                and abs(float(v_curr) - float(v_prev)) > 0.05
            ):
                delta = round(float(v_curr) - float(v_prev), 2)
                changes.append(
                    {
                        "category": "relative_power",
                        "country_iso3": iso3,
                        "country_name": cname,
                        "measurement": label,
                        "previous_value": round(float(v_prev), 2),
                        "current_value": round(float(v_curr), 2),
                        "difference": delta,
                        "observation_period": p_curr.get(p_key) or period,
                        "source": p_curr.get(s_key) or "Public macro providers",
                        "direction": "up" if delta > 0 else "down",
                    }
                )

    # 5. Data revisions from IndicatorRevision
    for rev in revisions or []:
        changes.append(rev)

    return {
        "changed_classifications_count": len(changed_countries),
        "changes": changes,
        "summary_message": (
            f"{len(changes)} genuine economic or revision change(s) detected."
            if changes
            else "No new economic changes detected."
        ),
    }


async def _recent_revisions_since(
    session: AsyncSession, since_dt: datetime | None, limit: int = 25
) -> list[dict[str, Any]]:
    if since_dt is None:
        return []
    q = (
        select(
            Country.iso3,
            Country.name,
            Indicator.name,
            Indicator.code,
            IndicatorRevision.old_value,
            IndicatorRevision.new_value,
            IndicatorRevision.delta,
            Observation.period_start,
            Observation.observation_date,
            DataSource.name,
        )
        .join(Observation, Observation.id == IndicatorRevision.new_observation_id)
        .join(Country, Country.id == Observation.country_id)
        .join(Indicator, Indicator.id == Observation.indicator_id)
        .join(DataSource, DataSource.id == Observation.data_source_id)
        .where(IndicatorRevision.created_at > since_dt)
        .order_by(desc(IndicatorRevision.created_at))
        .limit(limit)
    )
    rows = (await session.execute(q)).all()
    out: list[dict[str, Any]] = []
    for (
        iso3,
        cname,
        ind_name,
        ind_code,
        old_val,
        new_val,
        delta,
        p_start,
        obs_date,
        src_name,
    ) in rows:
        dt = p_start or obs_date
        diff = (
            round(float(delta), 4)
            if delta is not None
            else (
                round(float(new_val) - float(old_val), 4)
                if old_val is not None
                else None
            )
        )
        out.append(
            {
                "category": "revision",
                "country_iso3": iso3,
                "country_name": cname,
                "measurement": f"{ind_name} ({ind_code})",
                "previous_value": round(float(old_val), 4)
                if old_val is not None
                else None,
                "current_value": round(float(new_val), 4),
                "difference": diff,
                "observation_period": str(dt.year) if dt else None,
                "source": src_name,
                "direction": (
                    "up"
                    if (diff is not None and diff > 0)
                    else ("down" if (diff is not None and diff < 0) else "revised")
                ),
            }
        )
    return out


async def build_freshness_and_changes(
    session: AsyncSession, core: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    obs_dir = observatory_dir()
    latest_snap_file = obs_dir / "latest_snapshot.json"
    prev_snap_file = obs_dir / "previous_snapshot.json"
    state_file = obs_dir / "refresh_state.json"

    # Query DB ingestion metadata
    total_obs = int(
        (await session.execute(select(func.count(Observation.id)))).scalar() or 0
    )
    total_revs = int(
        (
            await session.execute(select(func.count(IndicatorRevision.id)))
        ).scalar()
        or 0
    )
    max_obs_period = (
        await session.execute(select(func.max(Observation.period_start)))
    ).scalar()
    latest_obs_period = (
        str(max_obs_period.year)
        if max_obs_period is not None
        else core["scoring_period"]
    )

    # Latest ingestion runs per provider
    run_rows = (
        await session.execute(
            select(
                DataSource.key,
                DataSource.name,
                IngestionRun.status,
                IngestionRun.completed_at,
                IngestionRun.started_at,
                IngestionRun.rows_inserted,
                IngestionRun.rows_revised,
                IngestionRun.error_count,
                IngestionRun.errors,
            )
            .join(DataSource, DataSource.id == IngestionRun.data_source_id)
            .order_by(desc(IngestionRun.id))
            .limit(120)
        )
    ).all()

    latest_collection_dt: datetime | None = None
    seen_sources: set[str] = set()
    provider_failures: list[dict[str, Any]] = []
    for (
        skey,
        sname,
        status,
        comp_at,
        start_at,
        _ins,
        _rev,
        err_cnt,
        errs,
    ) in run_rows:
        ts = comp_at or start_at
        if (
            status in (IngestionRunStatus.success, "success")
            and ts is not None
            and (latest_collection_dt is None or ts > latest_collection_dt)
        ):
            latest_collection_dt = ts
        if skey not in seen_sources:
            seen_sources.add(skey)
            status_val = status.value if hasattr(status, "value") else str(status)
            if status_val in ("failed", "partial") or (err_cnt and err_cnt > 0):
                provider_failures.append(
                    {
                        "provider": skey,
                        "provider_name": sname,
                        "latest_status": status_val,
                        "error_count": int(err_cnt or 1),
                        "last_run_at": to_utc_iso(ts),
                        "message": (
                            str(errs)[:160]
                            if errs
                            else f"{sname} reported {status_val}"
                        ),
                    }
                )

    if latest_collection_dt is None:
        max_retrieved = (
            await session.execute(select(func.max(Observation.retrieved_at)))
        ).scalar()
        latest_collection_dt = max_retrieved

    dialect = getattr(getattr(session, "bind", None), "dialect", None)
    is_sqlite = getattr(dialect, "name", "") == "sqlite"
    use_disk = not is_sqlite or bool(os.environ.get("BCA_OBSERVATORY_DIR"))

    curr_snap = extract_snapshot_record(core)
    saved_state: dict[str, Any] | None = None
    if use_disk and state_file.exists():
        try:
            saved_state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            saved_state = None

    if use_disk and not latest_snap_file.exists():
        # Seed baseline snapshot without fabricating artificial daily changes
        latest_snap_file.write_text(
            json.dumps(curr_snap, indent=2), encoding="utf-8"
        )

    prev_snap: dict[str, Any] | None = None
    if use_disk and prev_snap_file.exists():
        try:
            prev_snap = json.loads(prev_snap_file.read_text(encoding="utf-8"))
        except Exception:
            prev_snap = None

    if saved_state and saved_state.get("db_fingerprint") == core["db_fingerprint"]:
        status_code = saved_state.get("status", "no_new_observations")
        if provider_failures and status_code not in ("update_failed",):
            status_code = "partial_provider_failure"
        new_obs = int(saved_state.get("new_observations_count", 0))
        rev_cnt = int(saved_state.get("revisions_count", 0))
        chg_cls = int(saved_state.get("changed_classifications_count", 0))
        changes_list = saved_state.get("changes", [])
        summary_msg = saved_state.get(
            "summary_message", "No new economic changes detected."
        )
        calc_iso = saved_state.get("latest_calculation_at") or core["computed_at"]
        coll_iso = saved_state.get("latest_collection_at") or to_utc_iso(
            latest_collection_dt
        )
        attempt_iso = saved_state.get("latest_update_attempt_at")
        successful_iso = saved_state.get("latest_successful_update_at")
        all_failures = saved_state.get("provider_failures") or provider_failures
    else:
        diff = diff_snapshots(prev_snap, curr_snap)
        changes_list = diff["changes"]
        chg_cls = diff["changed_classifications_count"]
        summary_msg = diff["summary_message"]
        new_obs = 0
        rev_cnt = 0
        status_code = (
            "partial_provider_failure"
            if provider_failures
            else ("updated" if changes_list else "no_new_observations")
        )
        calc_iso = core["computed_at"]
        coll_iso = to_utc_iso(latest_collection_dt)
        attempt_iso = None
        successful_iso = None
        all_failures = provider_failures

    freshness = {
        "status": status_code,
        "status_label": {
            "updated": "Updated",
            "no_new_observations": "No new observations",
            "partial_provider_failure": "Partial provider failure",
            "update_failed": "Update failed",
        }.get(status_code, "No new observations"),
        "latest_collection_at": coll_iso,
        "latest_collection_zurich": to_zurich_display(coll_iso),
        "latest_update_attempt_at": attempt_iso,
        "latest_update_attempt_zurich": to_zurich_display(attempt_iso),
        "latest_successful_update_at": successful_iso,
        "latest_successful_update_zurich": to_zurich_display(successful_iso),
        "latest_calculation_at": calc_iso,
        "latest_calculation_zurich": to_zurich_display(calc_iso),
        "latest_observation_period": latest_obs_period,
        "scoring_period": core["scoring_period"],
        "timezone": "Europe/Zurich",
        "new_observations_count": new_obs,
        "revisions_count": rev_cnt,
        "changed_classifications_count": chg_cls,
        "provider_failures": all_failures,
        "total_observations": total_obs,
        "total_revisions": total_revs,
    }
    daily_changes = {
        "has_previous_snapshot": prev_snap is not None,
        "previous_snapshot_at": (
            prev_snap.get("calculated_at") if prev_snap else None
        ),
        "previous_snapshot_zurich": (
            to_zurich_display(prev_snap.get("calculated_at"))
            if prev_snap
            else None
        ),
        "current_snapshot_at": calc_iso,
        "current_snapshot_zurich": to_zurich_display(calc_iso),
        "summary_message": summary_msg,
        "changes": changes_list,
    }
    return freshness, daily_changes


async def _run_daily_refresh_workflow_unlocked(
    session: AsyncSession,
    model_id: str = "model_b_domain",
    collect_providers: bool = False,
    sources: list[str] | None = None,
    collection_summary: dict[str, Any] | None = None,
    persist_result: bool = True,
) -> dict[str, Any]:
    """Execute the §9 daily Big Cycle refresh & snapshot comparison workflow.

    1. Optional provider collection via existing run_ingestion (preserves immutable vintages).
    2. Recalculate forces & experimental cycle positions.
    3. Compare against previous successful snapshot.
    4. Persist snapshot & daily change record without generating artificial changes.
    """
    obs_dir = observatory_dir()
    latest_snap_file = obs_dir / "latest_snapshot.json"
    prev_snap_file = obs_dir / "previous_snapshot.json"
    state_file = obs_dir / "refresh_state.json"

    prior_state: dict[str, Any] | None = None
    if state_file.exists():
        try:
            prior_state = json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            prior_state = None

    prior_snap: dict[str, Any] | None = None
    if latest_snap_file.exists():
        try:
            prior_snap = json.loads(
                latest_snap_file.read_text(encoding="utf-8")
            )
        except Exception:
            prior_snap = None

    before_rev_time = datetime.now(timezone.utc)
    inserted = 0
    revised = 0
    provider_failures: list[dict[str, Any]] = []
    attempted_series = 0

    if collection_summary is not None:
        inserted = int(collection_summary.get("inserted", 0))
        revised = int(collection_summary.get("revised", 0))
        provider_failures = list(
            collection_summary.get("provider_failures", [])
        )
        attempted_series = int(collection_summary.get("attempted_series", 0))
        if collection_summary.get("started_at_dt"):
            started_raw = collection_summary["started_at_dt"]
            before_rev_time = (
                datetime.fromisoformat(started_raw)
                if isinstance(started_raw, str)
                else started_raw
            )
    elif collect_providers:
        summary = await collect_provider_observations(sources=sources)
        inserted = summary["inserted"]
        revised = summary["revised"]
        provider_failures = summary["provider_failures"]
        attempted_series = summary["attempted_series"]
        before_rev_time = summary["started_at_dt"]

    # If collection was attempted and EVERY series failed, preserve prior snapshot!
    if (
        attempted_series > 0
        and inserted == 0
        and revised == 0
        and sum(f.get("error_count", 1) for f in provider_failures)
        >= attempted_series
    ):
        now_iso = to_utc_iso(datetime.now(timezone.utc))
        failed_state = {
            "status": "update_failed",
            "db_fingerprint": await db_fingerprint(session),
            "latest_collection_at": now_iso,
            "latest_update_attempt_at": to_utc_iso(before_rev_time),
            "latest_successful_update_at": (
                (prior_state or {}).get("latest_successful_update_at")
            ),
            "latest_calculation_at": (
                prior_snap.get("calculated_at") if prior_snap else now_iso
            ),
            "new_observations_count": 0,
            "revisions_count": 0,
            "changed_classifications_count": 0,
            "provider_failures": provider_failures,
            "changes": [],
            "summary_message": "Update failed — previous verified calculations preserved.",
        }
        state_file.write_text(
            json.dumps(failed_state, indent=2), encoding="utf-8"
        )
        return failed_state

    # Clear memory cache so recalculation reflects any new DB rows
    _MEM_CACHE.clear()
    core = await compute_core_observatory(session, model_id=model_id)
    if not persist_result:
        return {
            "status": "recalculated",
            "model_id": model_id,
            "db_fingerprint": core["db_fingerprint"],
            "latest_collection_at": None,
            "latest_update_attempt_at": None,
            "latest_successful_update_at": (
                (prior_state or {}).get("latest_successful_update_at")
            ),
            "latest_calculation_at": to_utc_iso(datetime.now(timezone.utc)),
            "new_observations_count": inserted,
            "revisions_count": revised,
            "changed_classifications_count": 0,
            "provider_failures": provider_failures,
            "changes": [],
            "summary_message": (
                f"Experimental model {model_id} recalculated without "
                "replacing the reported snapshot."
            ),
        }
    curr_snap = extract_snapshot_record(core)
    revs = await _recent_revisions_since(session, before_rev_time)
    diff = diff_snapshots(prior_snap, curr_snap, revisions=revs)

    has_real_changes = bool(diff["changes"]) or inserted > 0 or revised > 0
    if prior_snap is None:
        latest_snap_file.write_text(
            json.dumps(curr_snap, indent=2), encoding="utf-8"
        )
    elif has_real_changes:
        prev_snap_file.write_text(
            json.dumps(prior_snap, indent=2), encoding="utf-8"
        )
        latest_snap_file.write_text(
            json.dumps(curr_snap, indent=2), encoding="utf-8"
        )

    if provider_failures:
        status_code = "partial_provider_failure"
    elif has_real_changes:
        status_code = "updated"
    else:
        status_code = "no_new_observations"

    now_iso = to_utc_iso(datetime.now(timezone.utc))
    attempted_collection = bool(collect_providers or collection_summary)
    attempt_iso = (
        to_utc_iso(before_rev_time)
        if attempted_collection
        else (prior_state or {}).get("latest_update_attempt_at")
    )
    successful_iso = (
        now_iso
        if status_code in {"updated", "no_new_observations"}
        else (prior_state or {}).get("latest_successful_update_at")
    )
    state = {
        "status": status_code,
        "db_fingerprint": core["db_fingerprint"],
        "latest_collection_at": now_iso if attempted_collection else None,
        "latest_update_attempt_at": attempt_iso,
        "latest_successful_update_at": successful_iso,
        "latest_calculation_at": now_iso,
        "new_observations_count": inserted,
        "revisions_count": revised,
        "changed_classifications_count": diff["changed_classifications_count"],
        "provider_failures": provider_failures,
        "changes": diff["changes"],
        "summary_message": diff["summary_message"],
    }
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


async def run_daily_refresh_workflow(
    session: AsyncSession,
    model_id: str = "model_b_domain",
    collect_providers: bool = False,
    sources: list[str] | None = None,
    collection_summary: dict[str, Any] | None = None,
    persist_result: bool = True,
) -> dict[str, Any]:
    """Run the refresh workflow under the shared cross-process update lock."""
    async with update_lock("observatory-refresh"):
        return await _run_daily_refresh_workflow_unlocked(
            session,
            model_id=model_id,
            collect_providers=collect_providers,
            sources=sources,
            collection_summary=collection_summary,
            persist_result=persist_result,
        )


async def collect_provider_observations(
    sources: list[str] | None = None,
) -> dict[str, Any]:
    """Reuse existing adapters + run_ingestion (never duplicates ingestion logic)."""
    from app.data_sources.bis import BISAdapter
    from app.data_sources.bis_mappings import BIS_MAPPINGS
    from app.data_sources.imf_weo import ImfWeoAdapter
    from app.data_sources.imf_weo_mappings import IMF_WEO_MAPPINGS
    from app.data_sources.oecd import OECDAdapter
    from app.data_sources.oecd_mappings import OECD_MAPPINGS
    from app.data_sources.world_bank import WorldBankAdapter
    from app.data_sources.world_bank_mappings import WORLD_BANK_MAPPINGS
    from app.services.ingestion_service import run_ingestion

    providers: dict[str, tuple[Any, Any]] = {
        "world_bank": (WorldBankAdapter, WORLD_BANK_MAPPINGS),
        "bis": (BISAdapter, BIS_MAPPINGS),
        "oecd": (OECDAdapter, OECD_MAPPINGS),
        "imf_weo": (ImfWeoAdapter, IMF_WEO_MAPPINGS),
    }
    if sources:
        providers = {k: v for k, v in providers.items() if k in sources}

    sm = get_sessionmaker()
    async with sm() as s:
        countries = [
            r[0]
            for r in (
                await s.execute(select(Country.iso3).order_by(Country.iso3))
            ).all()
        ]

    total_steps = sum(
        len(mappings) * len(countries) for _, mappings in providers.values()
    )
    started_at_dt = datetime.now(timezone.utc)
    _REFRESH_JOB.update(
        {
            "total_steps": total_steps,
            "completed_steps": 0,
            "inserted": 0,
            "revised": 0,
            "failed": 0,
        }
    )

    inserted = 0
    revised = 0
    attempted = 0
    provider_failures: list[dict[str, Any]] = []

    for source_key, (adapter_cls, mappings) in providers.items():
        _REFRESH_JOB["current_provider"] = source_key
        src_errors = 0
        last_err_msg = None
        adapter = adapter_cls()
        async with adapter:
            for m in mappings:
                for iso3 in countries:
                    attempted += 1
                    async with sm() as s:
                        try:
                            outcome = await run_ingestion(
                                s,
                                adapter,
                                country_iso3=iso3,
                                external_series_code=m.external_code,
                            )
                            await s.commit()
                            if outcome.error or outcome.persistence is None:
                                src_errors += 1
                                last_err_msg = outcome.error or "empty persistence"
                            else:
                                inserted += int(outcome.persistence.inserted or 0)
                                revised += int(outcome.persistence.revised or 0)
                        except Exception as exc:
                            await s.rollback()
                            src_errors += 1
                            last_err_msg = f"{type(exc).__name__}: {exc}"
                    _REFRESH_JOB["completed_steps"] = attempted
                    _REFRESH_JOB["inserted"] = inserted
                    _REFRESH_JOB["revised"] = revised
                    _REFRESH_JOB["failed"] += 1 if src_errors and last_err_msg else 0
        if src_errors > 0:
            provider_failures.append(
                {
                    "provider": source_key,
                    "provider_name": source_key,
                    "latest_status": (
                        "failed"
                        if src_errors >= len(mappings) * len(countries)
                        else "partial"
                    ),
                    "error_count": src_errors,
                    "last_run_at": to_utc_iso(datetime.now(timezone.utc)),
                    "message": last_err_msg or "provider ingestion error",
                }
            )

    return {
        "started_at_dt": started_at_dt,
        "attempted_series": attempted,
        "inserted": inserted,
        "revised": revised,
        "provider_failures": provider_failures,
    }


def get_refresh_job_status() -> dict[str, Any]:
    return dict(_REFRESH_JOB)


async def trigger_refresh_job(
    session: AsyncSession,
    model_id: str = "model_b_domain",
    collect_providers: bool = False,
    sources: list[str] | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Single-flight refresh control (§11). Returns (accepted, status_payload)."""
    if _REFRESH_LOCK.locked() or _REFRESH_JOB.get("running"):
        return False, get_refresh_job_status()
    shared_lock = update_lock_status()
    if shared_lock.get("locked"):
        return False, {
            **get_refresh_job_status(),
            "status": "locked",
            "update_lock": shared_lock,
        }

    if not collect_providers:
        async with _REFRESH_LOCK:
            _REFRESH_JOB.update(
                {
                    "running": True,
                    "mode": "recalculate",
                    "started_at": to_utc_iso(datetime.now(timezone.utc)),
                    "completed_at": None,
                    "current_provider": None,
                    "status": "running",
                    "error": None,
                }
            )
            try:
                state = await run_daily_refresh_workflow(
                    session, model_id=model_id, collect_providers=False
                )
                _REFRESH_JOB.update(
                    {
                        "running": False,
                        "completed_at": to_utc_iso(datetime.now(timezone.utc)),
                        "status": state["status"],
                    }
                )
                return True, {"job": get_refresh_job_status(), "result": state}
            except Exception as exc:
                _REFRESH_JOB.update(
                    {
                        "running": False,
                        "completed_at": to_utc_iso(datetime.now(timezone.utc)),
                        "status": "update_failed",
                        "error": str(exc),
                    }
                )
                raise

    # Background provider collection + recalculation (single-flight)
    async def _bg() -> None:
        async with _REFRESH_LOCK:
            _REFRESH_JOB.update(
                {
                    "running": True,
                    "mode": "collect",
                    "started_at": to_utc_iso(datetime.now(timezone.utc)),
                    "completed_at": None,
                    "current_provider": "starting",
                    "completed_steps": 0,
                    "total_steps": 0,
                    "inserted": 0,
                    "revised": 0,
                    "failed": 0,
                    "status": "running",
                    "error": None,
                }
            )
            try:
                summary = await collect_provider_observations(sources=sources)
                sm = get_sessionmaker()
                async with sm() as s:
                    state = await run_daily_refresh_workflow(
                        s,
                        model_id=model_id,
                        collect_providers=False,
                        collection_summary=summary,
                    )
                _REFRESH_JOB.update(
                    {
                        "running": False,
                        "current_provider": None,
                        "completed_at": to_utc_iso(datetime.now(timezone.utc)),
                        "status": state["status"],
                    }
                )
            except Exception as exc:
                _REFRESH_JOB.update(
                    {
                        "running": False,
                        "current_provider": None,
                        "completed_at": to_utc_iso(datetime.now(timezone.utc)),
                        "status": "update_failed",
                        "error": str(exc),
                    }
                )

    asyncio.create_task(_bg())
    await asyncio.sleep(0)
    return True, {"job": get_refresh_job_status()}
