"""Market data service (Mission 5 §14, §18, §23).

Instrument seeding, idempotent observation ingestion, history queries and
documented return calculations. Returns are computed only from stored raw
observations — missing dates are never filled with invented prices.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_sources.fred import MarketPriceDTO
from app.market.instruments import INSTRUMENTS, InstrumentSpec
from app.models import (
    Country,
    DataSource,
    IngestionRun,
    IngestionRunStatus,
    MarketInstrument,
    MarketObservation,
)

MARKET_CALC_VERSION = "market-calc-v1"


async def seed_instruments(session: AsyncSession) -> dict:
    """Insert/update the verified instrument registry. Idempotent."""
    source = (
        await session.execute(
            select(DataSource).where(DataSource.key == "fred")
        )
    ).scalar_one_or_none()
    if source is None:
        raise RuntimeError("DataSource 'fred' not seeded")

    countries = {
        c.iso3: c for c in (await session.execute(select(Country))).scalars()
    }
    existing = {
        i.code: i
        for i in (
            await session.execute(select(MarketInstrument))
        ).scalars()
    }
    inserted = updated = 0
    for spec in INSTRUMENTS:
        country_id = (
            countries[spec.country_iso3].id
            if spec.country_iso3 and spec.country_iso3 in countries
            else None
        )
        row = existing.get(spec.code)
        fields = {
            "name": spec.name,
            "asset_class": spec.asset_class,
            "return_methodology": spec.return_methodology,
            "country_id": country_id,
            "currency": spec.currency,
            "unit": spec.unit,
            "frequency": spec.frequency,
            "data_source_id": source.id,
            "external_code": spec.external_code,
            "quote_convention": spec.quote_convention,
            "notes": spec.notes,
        }
        if row is None:
            session.add(MarketInstrument(code=spec.code, **fields))
            inserted += 1
        else:
            for k, v in fields.items():
                setattr(row, k, v)
            updated += 1
    await session.flush()
    return {"inserted": inserted, "updated": updated,
            "total": len(INSTRUMENTS)}


async def persist_market_observations(
    session: AsyncSession,
    instrument: MarketInstrument,
    dtos: list[MarketPriceDTO],
) -> dict:
    """Idempotent: existing (instrument, obs_date) rows are skipped, never
    overwritten — raw provider values are immutable."""
    existing = {
        r[0]
        for r in (
            await session.execute(
                select(MarketObservation.obs_date).where(
                    MarketObservation.instrument_id == instrument.id
                )
            )
        ).all()
    }
    inserted = 0
    for dto in dtos:
        if dto.obs_date in existing:
            continue
        session.add(MarketObservation(
            instrument_id=instrument.id,
            obs_date=dto.obs_date,
            value=dto.value,
            retrieved_at=dto.retrieved_at,
            raw_payload=dto.raw_payload,
        ))
        inserted += 1
    await session.flush()
    return {"received": len(dtos), "inserted": inserted,
            "skipped": len(dtos) - inserted}


async def run_market_ingestion(
    session: AsyncSession,
    adapter,
    instrument: MarketInstrument,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> dict:
    """Fetch + persist one instrument, recording an IngestionRun."""
    from app.data_sources.base import (
        DataSourceError,
        DataSourceNoDataError,
    )

    run = IngestionRun(
        data_source_id=instrument.data_source_id,
        status=IngestionRunStatus.running,
        started_at=datetime.now(timezone.utc),
        run_metadata={
            "scope": "market",
            "instrument_code": instrument.code,
            "external_code": instrument.external_code,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
        },
    )
    session.add(run)
    await session.flush()
    try:
        dtos = await adapter.fetch_series(
            instrument.external_code, start=start, end=end
        )
    except DataSourceNoDataError:
        run.status = IngestionRunStatus.success
        run.completed_at = datetime.now(timezone.utc)
        meta = dict(run.run_metadata or {})
        meta["no_data"] = True
        run.run_metadata = meta
        await session.flush()
        return {"run_id": run.id, "status": "no_data"}
    except DataSourceError as exc:
        run.status = IngestionRunStatus.failed
        run.completed_at = datetime.now(timezone.utc)
        run.error_count = 1
        run.errors = [{"type": type(exc).__name__, "message": str(exc)}]
        await session.flush()
        return {"run_id": run.id, "status": "failed",
                "error": f"{type(exc).__name__}: {exc}"}

    result = await persist_market_observations(session, instrument, dtos)
    run.status = IngestionRunStatus.success
    run.completed_at = datetime.now(timezone.utc)
    run.rows_received = result["received"]
    run.rows_inserted = result["inserted"]
    run.rows_skipped = result["skipped"]
    await session.flush()
    return {"run_id": run.id, "status": "success", **result}


async def instrument_history(
    session: AsyncSession,
    code: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
    limit: int = 5000,
) -> tuple[MarketInstrument, list[MarketObservation]] | None:
    inst = (
        await session.execute(
            select(MarketInstrument).where(MarketInstrument.code == code)
        )
    ).scalar_one_or_none()
    if inst is None:
        return None
    q = (
        select(MarketObservation)
        .where(MarketObservation.instrument_id == inst.id)
        .order_by(MarketObservation.obs_date)
        .limit(limit)
    )
    if start:
        q = q.where(MarketObservation.obs_date >= start)
    if end:
        q = q.where(MarketObservation.obs_date <= end)
    rows = list((await session.execute(q)).scalars())
    return inst, rows


# --- §23 calculations — documented, minimum-sample gated ------------------------

MIN_OBS_RETURN = 20        # model assumption for return statistics
MIN_OBS_RISK = 60          # volatility/drawdown need more points


@dataclass(frozen=True)
class ReturnSeries:
    methodology: str           # e.g. "simple returns on price_index"
    points: tuple[tuple[str, float], ...]  # (obs_date iso, return)


def simple_returns(obs: list[tuple[date, float]]) -> ReturnSeries:
    """Simple period returns r_t = v_t / v_{t-1} - 1 on stored values.

    For price_index instruments this approximates price return (no
    dividends); for yield/FX/spot series it is a quote change, never a
    strategy return — the methodology string says which.
    """
    pts = [
        (b[0].isoformat(), b[1] / a[1] - 1.0)
        for a, b in zip(obs, obs[1:])
        if a[1] and b[1]
    ]
    return ReturnSeries("simple_return_on_stored_value", tuple(pts))


def performance_stats(
    obs: list[tuple[date, float]],
    periods_per_year: int,
) -> dict:
    """Cumulative/annualised return, volatility, max drawdown.

    periods_per_year: 252 daily, 12 monthly. Documented assumptions;
    no annualisation is reported when samples are below MIN_OBS_*.
    """
    values = [v for _, v in obs if v is not None]
    n = len(values)
    out: dict = {
        "observations": n,
        "methodology": "simple returns on stored values; "
                       "annualised via geometric mean / sqrt-scaling",
        "periods_per_year": periods_per_year,
        "sufficient_for_return": n >= MIN_OBS_RETURN,
        "sufficient_for_risk": n >= MIN_OBS_RISK,
    }
    if n < 2:
        return out
    out["cumulative_return"] = values[-1] / values[0] - 1.0
    if n >= MIN_OBS_RETURN:
        years = n / periods_per_year
        if years > 0 and values[0] > 0 and values[-1] > 0:
            out["annualised_return"] = (values[-1] / values[0]) ** (1 / years) - 1
    if n >= MIN_OBS_RISK:
        rets = [b / a - 1 for a, b in zip(values, values[1:]) if a]
        out["volatility"] = (
            statistics.pstdev(rets) * math.sqrt(periods_per_year)
            if len(rets) > 1 else None
        )
        peak, mdd = values[0], 0.0
        for v in values:
            peak = max(peak, v)
            mdd = min(mdd, v / peak - 1.0)
        out["max_drawdown"] = mdd
    return out


def rolling_stat(
    obs: list[tuple[date, float]], window: int, kind: str = "volatility",
    periods_per_year: int = 252,
) -> list[dict]:
    """Rolling window returns or volatility — window must be full."""
    values = [(d, v) for d, v in obs if v is not None]
    out = []
    for i in range(window, len(values) + 1):
        w = values[i - window: i]
        if kind == "return":
            val = w[-1][1] / w[0][1] - 1.0
        else:
            rets = [b[1] / a[1] - 1 for a, b in zip(w, w[1:]) if a[1]]
            val = (
                statistics.pstdev(rets) * math.sqrt(periods_per_year)
                if len(rets) > 1 else None
            )
        if val is not None:
            out.append({"date": w[-1][0].isoformat(), "value": val})
    return out


def correlation_matrix(
    series: dict[str, list[tuple[date, float]]],
) -> dict:
    """Pairwise Pearson correlation of simple returns on shared dates.

    Only dates present in BOTH series are used — no forward-filling.
    """
    returns = {}
    for name, obs in series.items():
        r = {}
        for a, b in zip(obs, obs[1:]):
            if a[1] and b[1]:
                r[b[0]] = b[1] / a[1] - 1.0
        returns[name] = r

    names = sorted(returns)
    pairs = {}
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            shared = sorted(set(returns[x]) & set(returns[y]))
            if len(shared) < MIN_OBS_RETURN:
                pairs[f"{x}|{y}"] = {
                    "shared_obs": len(shared), "correlation": None,
                }
                continue
            xs = [returns[x][d] for d in shared]
            ys = [returns[y][d] for d in shared]
            pairs[f"{x}|{y}"] = {
                "shared_obs": len(shared),
                "correlation": _pearson(xs, ys),
            }
    return {"methodology": "pearson correlation of simple returns on "
                            "shared observation dates only",
            "pairs": pairs}


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 2:
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    vx = sum((a - mx) ** 2 for a in xs)
    vy = sum((b - my) ** 2 for b in ys)
    if vx == 0 or vy == 0:
        return None
    return cov / math.sqrt(vx * vy)
