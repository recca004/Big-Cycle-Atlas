"""Sprint 6.10 tests: DerivedAlignedValue architectural contract (DEC-037).

These tests prove the six required invariants of the derived aligned layer:

1. Country mixing is rejected.
2. Component provenance remains independent (no collapse to synthetic identity).
3. Missing required input does not become zero (MISSING != ZERO).
4. Different component vintages remain distinct.
5. An unsafe component makes the derived result non-backtest-safe.
6. Derivation does not create a raw Observation (typed contract only — no DB,
   no persistence, no Observation rows).

The dataclasses are non-executable: they perform validation only and never
query the database. No external APIs, no live data, no DB writes.
"""
from datetime import date

import pytest

from app.cycle.normalization_definitions import (
    AlignedValue,
    DerivedAlignedValue,
    DerivedComponentProvenance,
    ScoringPeriod,
)


# --- Helpers ------------------------------------------------------------------

SP = ScoringPeriod(2025, 4)


def _aligned(
    indicator: str,
    country: str = "USA",
    sp: ScoringPeriod = SP,
    source_period: str = "2024",
    raw_value: float = 50.0,
    vintage: int = 1,
) -> AlignedValue:
    return AlignedValue(
        indicator_code=indicator,
        country_iso3=country,
        scoring_period=sp,
        source_period=source_period,
        raw_value=raw_value,
        age_periods=4,
        effective_period_end=date(2024, 12, 31),
        freshness_factor=0.9,
        is_stale=False,
        vintage_number=vintage,
    )


def _present_comp(
    indicator: str,
    av: AlignedValue,
    obs_id: int = 1,
    ss_id: int = 10,
    ds_id: int = 100,
    backtest_safe: bool = False,
) -> DerivedComponentProvenance:
    return DerivedComponentProvenance(
        indicator_code=indicator,
        aligned_value=av,
        observation_id=obs_id,
        source_series_id=ss_id,
        data_source_id=ds_id,
        component_backtest_safe=backtest_safe,
    )


def _missing_comp(indicator: str, reason: str = "no eligible observation") -> DerivedComponentProvenance:
    return DerivedComponentProvenance(
        indicator_code=indicator,
        aligned_value=None,
        missing_reason=reason,
    )


# --- 1. Country mixing is rejected -------------------------------------------


def test_country_mixing_rejected():
    """Invariant 1: a mixed-country derivation must be rejected."""
    av_usa = _aligned("EXPORTS_GDP", country="USA")
    av_che = _aligned("IMPORTS_GDP", country="CHE")
    with pytest.raises(ValueError, match="country isolation violated"):
        DerivedAlignedValue(
            derived_indicator_code="TRADE_OPENNESS_GDP",
            country_iso3="USA",
            scoring_period=SP,
            formula_id="sum_two_components",
            formula_version="derived-formula-v0.1",
            components=(
                _present_comp("EXPORTS_GDP", av_usa, obs_id=1, ss_id=10, ds_id=100),
                _present_comp("IMPORTS_GDP", av_che, obs_id=2, ss_id=20, ds_id=100),
            ),
            derived_value=50.0 + 40.0,
        )


def test_derived_country_must_match_components():
    """The derived country_iso3 must match every present component's country."""
    av1 = _aligned("EXPORTS_GDP", country="USA")
    av2 = _aligned("IMPORTS_GDP", country="USA")
    with pytest.raises(ValueError, match="country isolation violated"):
        DerivedAlignedValue(
            derived_indicator_code="TRADE_OPENNESS_GDP",
            country_iso3="CHE",  # mismatch
            scoring_period=SP,
            formula_id="sum_two_components",
            formula_version="derived-formula-v0.1",
            components=(
                _present_comp("EXPORTS_GDP", av1),
                _present_comp("IMPORTS_GDP", av2),
            ),
            derived_value=90.0,
        )


# --- 2. Component provenance remains independent ------------------------------


def test_component_provenance_independent():
    """Invariant 2: each component retains independent observation/source identities."""
    av1 = _aligned("EXPORTS_GDP", country="USA", vintage=1)
    av2 = _aligned("IMPORTS_GDP", country="USA", vintage=3)
    dav = DerivedAlignedValue(
        derived_indicator_code="TRADE_OPENNESS_GDP",
        country_iso3="USA",
        scoring_period=SP,
        formula_id="sum_two_components",
        formula_version="derived-formula-v0.1",
        components=(
            _present_comp("EXPORTS_GDP", av1, obs_id=101, ss_id=10, ds_id=1),
            _present_comp("IMPORTS_GDP", av2, obs_id=202, ss_id=20, ds_id=1),
        ),
        derived_value=100.0,
    )
    c0, c1 = dav.components
    # Independent observation identities
    assert c0.observation_id == 101
    assert c1.observation_id == 202
    assert c0.observation_id != c1.observation_id
    # Independent source-series identities
    assert c0.source_series_id == 10
    assert c1.source_series_id == 20
    assert c0.source_series_id != c1.source_series_id
    # Independent indicator codes
    assert c0.indicator_code == "EXPORTS_GDP"
    assert c1.indicator_code == "IMPORTS_GDP"
    # The derived value does NOT collapse them into one synthetic identity
    assert dav.derived_indicator_code == "TRADE_OPENNESS_GDP"
    assert dav.derived_indicator_code not in {c0.indicator_code, c1.indicator_code}


# --- 3. Missing required input does not become zero ---------------------------


def test_missing_component_produces_none_not_zero():
    """Invariant 3: a missing required component -> derived_value None, never 0."""
    av1 = _aligned("EXPORTS_GDP", country="USA")
    dav = DerivedAlignedValue(
        derived_indicator_code="TRADE_OPENNESS_GDP",
        country_iso3="USA",
        scoring_period=SP,
        formula_id="sum_two_components",
        formula_version="derived-formula-v0.1",
        components=(
            _present_comp("EXPORTS_GDP", av1),
            _missing_comp("IMPORTS_GDP", "no eligible observation for 2025-Q4"),
        ),
        derived_value=None,  # missing -> None, never 0
    )
    assert dav.derived_value is None
    # The missing component's reason is preserved
    missing = [c for c in dav.components if c.aligned_value is None]
    assert len(missing) == 1
    assert missing[0].indicator_code == "IMPORTS_GDP"
    assert "no eligible observation" in missing[0].missing_reason


def test_missing_component_with_nonzero_derived_value_rejected():
    """If any component is missing, a non-None derived_value must be rejected."""
    av1 = _aligned("EXPORTS_GDP", country="USA")
    with pytest.raises(ValueError, match="MISSING != ZERO"):
        DerivedAlignedValue(
            derived_indicator_code="TRADE_OPENNESS_GDP",
            country_iso3="USA",
            scoring_period=SP,
            formula_id="sum_two_components",
            formula_version="derived-formula-v0.1",
            components=(
                _present_comp("EXPORTS_GDP", av1),
                _missing_comp("IMPORTS_GDP"),
            ),
            derived_value=50.0,  # illegal: a component is missing
        )


def test_missing_component_provenance_carries_reason():
    """A missing component must carry a missing_reason explaining the absence."""
    comp = _missing_comp("IMPORTS_GDP", "no eligible observation")
    assert comp.aligned_value is None
    assert comp.missing_reason == "no eligible observation"
    assert comp.observation_id is None
    assert comp.source_series_id is None


# --- 4. Different component vintages remain distinct --------------------------


def test_different_vintages_remain_distinct():
    """Invariant 4: components may have different vintages — they stay distinct."""
    av1 = _aligned("EXPORTS_GDP", country="USA", vintage=1)
    av2 = _aligned("IMPORTS_GDP", country="USA", vintage=3)
    dav = DerivedAlignedValue(
        derived_indicator_code="TRADE_OPENNESS_GDP",
        country_iso3="USA",
        scoring_period=SP,
        formula_id="sum_two_components",
        formula_version="derived-formula-v0.1",
        components=(
            _present_comp("EXPORTS_GDP", av1),
            _present_comp("IMPORTS_GDP", av2),
        ),
        derived_value=100.0,
    )
    c0, c1 = dav.components
    assert c0.aligned_value.vintage_number == 1
    assert c1.aligned_value.vintage_number == 3
    assert c0.aligned_value.vintage_number != c1.aligned_value.vintage_number


# --- 5. Unsafe component makes derived non-backtest-safe -----------------------


def test_unsafe_component_makes_derived_unsafe():
    """Invariant 5: an unsafe component -> derived backtest_safe must be False."""
    av1 = _aligned("EXPORTS_GDP", country="USA")
    av2 = _aligned("IMPORTS_GDP", country="USA")
    dav = DerivedAlignedValue(
        derived_indicator_code="TRADE_OPENNESS_GDP",
        country_iso3="USA",
        scoring_period=SP,
        formula_id="sum_two_components",
        formula_version="derived-formula-v0.1",
        components=(
            _present_comp("EXPORTS_GDP", av1, backtest_safe=False),
            _present_comp("IMPORTS_GDP", av2, backtest_safe=False),
        ),
        derived_value=100.0,
        backtest_safe=False,  # both components unsafe -> derived unsafe
    )
    assert dav.backtest_safe is False


def test_backtest_safe_requires_all_components_safe():
    """backtest_safe=True with an unsafe component must be rejected."""
    av1 = _aligned("EXPORTS_GDP", country="USA")
    av2 = _aligned("IMPORTS_GDP", country="USA")
    with pytest.raises(ValueError, match="backtest_safe=True requires ALL"):
        DerivedAlignedValue(
            derived_indicator_code="TRADE_OPENNESS_GDP",
            country_iso3="USA",
            scoring_period=SP,
            formula_id="sum_two_components",
            formula_version="derived-formula-v0.1",
            components=(
                _present_comp("EXPORTS_GDP", av1, backtest_safe=True),
                _present_comp("IMPORTS_GDP", av2, backtest_safe=False),  # unsafe
            ),
            derived_value=100.0,
            backtest_safe=True,  # illegal: one component is unsafe
        )


def test_all_safe_components_allow_backtest_safe():
    """When all present components are safe, backtest_safe=True is allowed."""
    av1 = _aligned("EXPORTS_GDP", country="USA")
    av2 = _aligned("IMPORTS_GDP", country="USA")
    dav = DerivedAlignedValue(
        derived_indicator_code="TRADE_OPENNESS_GDP",
        country_iso3="USA",
        scoring_period=SP,
        formula_id="sum_two_components",
        formula_version="derived-formula-v0.1",
        components=(
            _present_comp("EXPORTS_GDP", av1, backtest_safe=True),
            _present_comp("IMPORTS_GDP", av2, backtest_safe=True),
        ),
        derived_value=100.0,
        backtest_safe=True,
    )
    assert dav.backtest_safe is True


# --- 6. Derivation does not create a raw Observation ---------------------------


def test_derivation_does_not_create_observation():
    """Invariant 6: DerivedAlignedValue is a typed contract, not a DB row.

    The dataclass has no database dependency, no session, no query, no
    persist_observations call. It cannot create an Observation row. This test
    constructs a derived value purely in memory — no DB session is involved.
    """
    av1 = _aligned("EXPORTS_GDP", country="USA")
    av2 = _aligned("IMPORTS_GDP", country="USA")
    dav = DerivedAlignedValue(
        derived_indicator_code="TRADE_OPENNESS_GDP",
        country_iso3="USA",
        scoring_period=SP,
        formula_id="sum_two_components",
        formula_version="derived-formula-v0.1",
        components=(
            _present_comp("EXPORTS_GDP", av1),
            _present_comp("IMPORTS_GDP", av2),
        ),
        derived_value=100.0,
    )
    # The derived value is a frozen dataclass, not an Observation model
    assert type(dav).__name__ == "DerivedAlignedValue"
    # It carries a distinct derived_indicator_code, not a provider indicator
    assert dav.derived_indicator_code == "TRADE_OPENNESS_GDP"
    # No Observation attributes exist on it
    assert not hasattr(dav, "period_start")
    assert not hasattr(dav, "country_id")
    assert not hasattr(dav, "indicator_id")
    assert not hasattr(dav, "source_series_id")


# --- Structural validation ----------------------------------------------------


def test_minimum_two_components_required():
    """A single observation is not a derivation — at least 2 components required."""
    av1 = _aligned("EXPORTS_GDP", country="USA")
    with pytest.raises(ValueError, match="at least 2 components"):
        DerivedAlignedValue(
            derived_indicator_code="TRADE_OPENNESS_GDP",
            country_iso3="USA",
            scoring_period=SP,
            formula_id="sum_two_components",
            formula_version="derived-formula-v0.1",
            components=(
                _present_comp("EXPORTS_GDP", av1),
            ),
            derived_value=50.0,
        )


def test_scoring_period_mismatch_rejected():
    """All present components must be aligned to the same scoring period."""
    av1 = _aligned("EXPORTS_GDP", country="USA", sp=ScoringPeriod(2025, 4))
    av2 = _aligned("IMPORTS_GDP", country="USA", sp=ScoringPeriod(2024, 4))
    with pytest.raises(ValueError, match="scoring period mismatch"):
        DerivedAlignedValue(
            derived_indicator_code="TRADE_OPENNESS_GDP",
            country_iso3="USA",
            scoring_period=ScoringPeriod(2025, 4),
            formula_id="sum_two_components",
            formula_version="derived-formula-v0.1",
            components=(
                _present_comp("EXPORTS_GDP", av1),
                _present_comp("IMPORTS_GDP", av2),
            ),
            derived_value=100.0,
        )


def test_formula_id_and_version_travel_with_value():
    """Formula identity and version are mandatory and travel with every value."""
    av1 = _aligned("EXPORTS_GDP", country="USA")
    av2 = _aligned("IMPORTS_GDP", country="USA")
    dav = DerivedAlignedValue(
        derived_indicator_code="TRADE_OPENNESS_GDP",
        country_iso3="USA",
        scoring_period=SP,
        formula_id="sum_two_components",
        formula_version="derived-formula-v0.1",
        components=(
            _present_comp("EXPORTS_GDP", av1),
            _present_comp("IMPORTS_GDP", av2),
        ),
        derived_value=100.0,
    )
    assert dav.formula_id == "sum_two_components"
    assert dav.formula_version == "derived-formula-v0.1"
    # Formula version is a separate namespace from normalization/force-aggregation
    assert "normalization" not in dav.formula_version
    assert "force-aggregation" not in dav.formula_version


def test_present_component_requires_source_identity():
    """A present component must carry observation_id, source_series_id, data_source_id."""
    av = _aligned("EXPORTS_GDP", country="USA")
    with pytest.raises(ValueError, match="requires observation_id"):
        DerivedComponentProvenance(
            indicator_code="EXPORTS_GDP",
            aligned_value=av,
            # missing observation_id, source_series_id, data_source_id
        )


def test_present_component_cannot_have_missing_reason():
    """A present component with a missing_reason is a contradiction."""
    av = _aligned("EXPORTS_GDP", country="USA")
    with pytest.raises(ValueError, match="present component cannot have a missing_reason"):
        DerivedComponentProvenance(
            indicator_code="EXPORTS_GDP",
            aligned_value=av,
            observation_id=1,
            source_series_id=10,
            data_source_id=100,
            missing_reason="should not be here",
        )


def test_missing_component_requires_reason():
    """A missing component without a missing_reason is a contradiction."""
    with pytest.raises(ValueError, match="missing component requires a missing_reason"):
        DerivedComponentProvenance(
            indicator_code="IMPORTS_GDP",
            aligned_value=None,
            # missing missing_reason
        )
