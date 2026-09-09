"""Auxiliary indicator diagnostics: typed DTO, immutable persistence,
exact-period lookup (DEC-022, Sprint 5.14).

Structurally separate from `persist_observations` — a diagnostic can
never become an Observation or enter alignment / force coverage / the
normalization registry. Diagnostics describe ONE provider estimate at ONE
source period: lookups are exact-period (no borrowing a prior year, no
latest-today fallback), country-scoped, and tied to the EXPECTED
provider-series identity.

Caller owns the transaction: no commit inside these helpers.
"""
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timezone
from typing import Iterable, Optional

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.data_sources.wgi_diagnostic_specs import WgiDiagnosticSpec
from app.models.country import Country
from app.models.data_source import DataSource
from app.models.indicator import Indicator
from app.models.indicator_diagnostic import (
    IndicatorDiagnostic,
    IndicatorDiagnosticKind,
)


class IndicatorDiagnosticPersistenceError(Exception):
    """A diagnostic DTO could not be resolved to a consistent DB identity."""


class IndicatorDiagnosticLookupError(Exception):
    """A diagnostics lookup could not resolve its base identities."""


class IndicatorDiagnosticAmbiguityError(IndicatorDiagnosticLookupError):
    """Rows for a logical diagnostic identity do not match the expected
    provider-series identity — never resolved by row order."""


@dataclass
class DiagnosticPersistenceResult:
    received: int
    inserted: int
    skipped: int
    revised: int


@dataclass(frozen=True)
class _ResolvedSpec:
    source_key: str
    provider_source_code: str
    provider_series_code: str
    diagnostic_kind: IndicatorDiagnosticKind
    base_indicator_code: str


class IndicatorDiagnosticDTO(BaseModel):
    """One raw provider diagnostic about a base canonical indicator's
    estimate. Deliberately NOT an ObservationDTO and never persisted
    through `persist_observations`."""

    country_iso3: str
    base_indicator_code: str
    source_key: str
    provider_source_code: str
    provider_series_code: str
    diagnostic_kind: IndicatorDiagnosticKind
    period_start: date
    value: float
    retrieved_at: datetime
    raw_payload: Optional[dict] = None


def _as_utc(dt: date | datetime) -> datetime:
    if isinstance(dt, datetime):
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.combine(dt, time.min, tzinfo=timezone.utc)


def _validate_value(kind: IndicatorDiagnosticKind, value: float) -> None:
    if not math.isfinite(value):
        raise IndicatorDiagnosticPersistenceError(
            f"Diagnostic value must be finite, got {value!r}"
        )
    if kind is IndicatorDiagnosticKind.source_count:
        if value < 0:
            raise IndicatorDiagnosticPersistenceError(
                f"source_count must be non-negative, got {value}"
            )
        if value != int(value):
            # No silent rounding 9.7 -> 10 — the provider value either is
            # an integer count or it is rejected.
            raise IndicatorDiagnosticPersistenceError(
                f"source_count must be integer-valued, got {value}"
            )


async def persist_indicator_diagnostics(
    session: AsyncSession,
    dtos: list[IndicatorDiagnosticDTO],
    specs: Iterable[WgiDiagnosticSpec],
) -> DiagnosticPersistenceResult:
    """Resolve DTO identities and persist valid diagnostics.

    Idempotent and immutable like the observation path: compared against
    the latest vintage for the FULL diagnostic identity (country, base
    indicator, data source, provider source, provider series, kind,
    period) — same value -> skipped; changed value -> a NEW vintage row is
    inserted and the old row is preserved. Historical values are never
    UPDATEd in place.

    Every DTO must match an expected spec's provider identity exactly;
    unknown identities are rejected rather than stored free-form.
    Uses add/flush only — commit ownership stays with the caller.
    """
    spec_index: dict[tuple[str, IndicatorDiagnosticKind], _ResolvedSpec] = {}
    for spec in specs:
        key = (spec.base_indicator_code, spec.diagnostic_kind)
        if key in spec_index:
            raise IndicatorDiagnosticPersistenceError(
                f"Duplicate spec for identity {key}"
            )
        spec_index[key] = _ResolvedSpec(
            source_key=spec.source_key,
            provider_source_code=spec.provider_source_code,
            provider_series_code=spec.provider_series_code,
            diagnostic_kind=spec.diagnostic_kind,
            base_indicator_code=spec.base_indicator_code,
        )

    result = DiagnosticPersistenceResult(received=len(dtos), inserted=0, skipped=0, revised=0)

    countries: dict[str, Country] = {}
    sources: dict[str, DataSource] = {}
    indicators: dict[str, Indicator] = {}

    async def _country(iso3: str) -> Country:
        if iso3 not in countries:
            row = (
                await session.execute(select(Country).where(Country.iso3 == iso3))
            ).scalar_one_or_none()
            if row is None:
                raise IndicatorDiagnosticPersistenceError(
                    f"Unknown country iso3: {iso3!r}"
                )
            countries[iso3] = row
        return countries[iso3]

    async def _source(key: str) -> DataSource:
        if key not in sources:
            row = (
                await session.execute(select(DataSource).where(DataSource.key == key))
            ).scalar_one_or_none()
            if row is None:
                raise IndicatorDiagnosticPersistenceError(
                    f"Unknown data source key: {key!r}"
                )
            sources[key] = row
        return sources[key]

    async def _indicator(code: str) -> Indicator:
        if code not in indicators:
            row = (
                await session.execute(select(Indicator).where(Indicator.code == code))
            ).scalar_one_or_none()
            if row is None:
                raise IndicatorDiagnosticPersistenceError(
                    f"Unknown base indicator code: {code!r}"
                )
            indicators[code] = row
        return indicators[code]

    for dto in dtos:
        spec = spec_index.get((dto.base_indicator_code, dto.diagnostic_kind))
        if spec is None:
            raise IndicatorDiagnosticPersistenceError(
                f"No expected diagnostic spec for base indicator "
                f"{dto.base_indicator_code!r} kind {dto.diagnostic_kind!s} — "
                f"unknown diagnostic identities are rejected"
            )
        if (
            dto.source_key,
            dto.provider_source_code,
            dto.provider_series_code,
        ) != (
            spec.source_key,
            spec.provider_source_code,
            spec.provider_series_code,
        ):
            raise IndicatorDiagnosticPersistenceError(
                f"DTO provider identity ({dto.source_key!r}, "
                f"{dto.provider_source_code!r}, {dto.provider_series_code!r}) "
                f"does not match the expected spec "
                f"({spec.source_key!r}, {spec.provider_source_code!r}, "
                f"{spec.provider_series_code!r})"
            )

        country = await _country(dto.country_iso3)
        source = await _source(dto.source_key)
        indicator = await _indicator(dto.base_indicator_code)
        _validate_value(dto.diagnostic_kind, dto.value)
        period_start = _as_utc(dto.period_start)

        latest = (
            await session.execute(
                select(IndicatorDiagnostic)
                .where(
                    IndicatorDiagnostic.country_id == country.id,
                    IndicatorDiagnostic.indicator_id == indicator.id,
                    IndicatorDiagnostic.data_source_id == source.id,
                    IndicatorDiagnostic.provider_source_code == dto.provider_source_code,
                    IndicatorDiagnostic.provider_series_code == dto.provider_series_code,
                    IndicatorDiagnostic.diagnostic_kind == dto.diagnostic_kind,
                    IndicatorDiagnostic.period_start == period_start,
                )
                .order_by(
                    IndicatorDiagnostic.vintage_number.desc(),
                    IndicatorDiagnostic.id.desc(),
                )
                .limit(1)
            )
        ).scalar_one_or_none()

        if latest is not None and latest.value == dto.value:
            result.skipped += 1
            continue

        session.add(
            IndicatorDiagnostic(
                country_id=country.id,
                indicator_id=indicator.id,
                data_source_id=source.id,
                diagnostic_kind=dto.diagnostic_kind,
                provider_source_code=dto.provider_source_code,
                provider_series_code=dto.provider_series_code,
                period_start=period_start,
                value=dto.value,
                retrieved_at=_as_utc(dto.retrieved_at),
                vintage_number=1 if latest is None else latest.vintage_number + 1,
                raw_payload=dto.raw_payload,
            )
        )
        if latest is None:
            result.inserted += 1
        else:
            result.revised += 1

    await session.flush()
    return result


async def get_indicator_diagnostics_for_period(
    session: AsyncSession,
    country_iso3: str,
    base_indicator_code: str,
    period_start: date | datetime,
    expected_specs: Iterable[WgiDiagnosticSpec],
) -> dict[IndicatorDiagnosticKind, Optional[float]]:
    """Latest-vintage diagnostics by kind, at the EXACT source period.

    Measurement uncertainty describes THAT provider estimate: a 2023 score
    never borrows 2022 bounds, today's source count, or another country's
    values. Lookup is tied to the EXPECTED provider-series identity — if
    rows exist for the logical identity (country, base indicator, kind,
    period) under a different provider series, the ambiguity is raised,
    never resolved by row order. Missing diagnostics are None — no
    synthetic rows, no zeros, no confidence implication.
    """
    country = (
        await session.execute(select(Country).where(Country.iso3 == country_iso3))
    ).scalar_one_or_none()
    if country is None:
        raise IndicatorDiagnosticLookupError(f"Unknown country iso3: {country_iso3!r}")
    indicator = (
        await session.execute(
            select(Indicator).where(Indicator.code == base_indicator_code)
        )
    ).scalar_one_or_none()
    if indicator is None:
        raise IndicatorDiagnosticLookupError(
            f"Unknown base indicator code: {base_indicator_code!r}"
        )
    period = _as_utc(period_start)

    values: dict[IndicatorDiagnosticKind, Optional[float]] = {}
    for spec in expected_specs:
        if spec.base_indicator_code != base_indicator_code:
            raise IndicatorDiagnosticLookupError(
                f"Spec for {spec.base_indicator_code!r} does not match the "
                f"requested base indicator {base_indicator_code!r}"
            )
        source = (
            await session.execute(
                select(DataSource).where(DataSource.key == spec.source_key)
            )
        ).scalar_one_or_none()
        if source is None:
            raise IndicatorDiagnosticLookupError(
                f"Unknown data source key: {spec.source_key!r}"
            )

        rows = (
            await session.execute(
                select(IndicatorDiagnostic).where(
                    IndicatorDiagnostic.country_id == country.id,
                    IndicatorDiagnostic.indicator_id == indicator.id,
                    IndicatorDiagnostic.diagnostic_kind == spec.diagnostic_kind,
                    IndicatorDiagnostic.period_start == period,
                )
            )
        ).scalars().all()

        expected_identity = (source.id, spec.provider_source_code, spec.provider_series_code)
        identities = {
            (row.data_source_id, row.provider_source_code, row.provider_series_code)
            for row in rows
        }
        if len(identities) > 1:
            # Multiple current rows from DIFFERENT provider series all claim
            # the same logical diagnostic — never resolved by row order; a
            # provider-series replacement must be an explicit spec change.
            raise IndicatorDiagnosticAmbiguityError(
                f"Multiple provider identities {sorted(identities)} claim "
                f"({country_iso3}, {base_indicator_code}, "
                f"{spec.diagnostic_kind!s}, {period.date()}) — expected "
                f"({spec.provider_source_code!r}, {spec.provider_series_code!r})"
            )

        if not identities or expected_identity not in identities:
            # Missing stays missing — no zero, no default, no fallback
            # period, and never a silent substitution of whichever series
            # happens to exist.
            values[spec.diagnostic_kind] = None
            continue

        # Exactly one provider identity holds this logical diagnostic and it
        # matches the expected spec — select its latest vintage.
        max_vintage = max(row.vintage_number for row in rows)
        latest = [row for row in rows if row.vintage_number == max_vintage]
        if len(latest) != 1:
            raise IndicatorDiagnosticAmbiguityError(
                f"Multiple rows at vintage {max_vintage} for "
                f"({country_iso3}, {base_indicator_code}, "
                f"{spec.diagnostic_kind!s}, {period.date()})"
            )
        values[spec.diagnostic_kind] = latest[0].value

    return values