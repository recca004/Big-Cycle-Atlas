"""WGI diagnostic spec registry (DEC-022, Sprint 5.14).

Provider-diagnostic metadata ONLY: the exact external series that carries
each auxiliary diagnostic for the three WGI score indicators. This
registry deliberately seeds nothing — no SourceSeries rows, no canonical
indicators, no observations. It exists so persistence and lookup can
enforce an EXPECTED provider-series identity instead of accepting
whichever series happens to exist (Part 13 of the Sprint 5.14 brief).

Series codes verified live against WB API v2 on 2026-09-09 (Sprint 5.13):
the uncertainty series live in the DEDICATED WGI source (provider source
id 3), distinct from the WDI source (id 2) that carries the score series
GOV_WGI_{RL,CC,PV}_SC. SE (standard error of the estimate) is
deliberately NOT in the input set (DEC-022).
"""
from dataclasses import dataclass

from app.models.indicator_diagnostic import IndicatorDiagnosticKind

# The WGI uncertainty series are published through the World Bank adapter
# but under the dedicated WGI source (id 3), NOT the WDI source (id 2)
# that carries the score series.
WGI_DIAGNOSTIC_SOURCE_KEY = "world_bank"
WGI_DIAGNOSTIC_PROVIDER_SOURCE_CODE = "3"

WGI_BASE_INDICATORS = (
    "RULE_OF_LAW_WGI_SCORE",
    "CONTROL_OF_CORRUPTION_WGI_SCORE",
    "POLITICAL_STABILITY_WGI_SCORE",
)

_DIMENSION_SERIES_PREFIX = {
    "RULE_OF_LAW_WGI_SCORE": "GOV_WGI_RL",
    "CONTROL_OF_CORRUPTION_WGI_SCORE": "GOV_WGI_CC",
    "POLITICAL_STABILITY_WGI_SCORE": "GOV_WGI_PV",
}

_KIND_SUFFIX = {
    IndicatorDiagnosticKind.ci_lower_bound: ".SC_LB",
    IndicatorDiagnosticKind.ci_upper_bound: ".SC_UB",
    IndicatorDiagnosticKind.source_count: ".SR",
}


@dataclass(frozen=True)
class WgiDiagnosticSpec:
    base_indicator_code: str
    diagnostic_kind: IndicatorDiagnosticKind
    source_key: str
    provider_source_code: str
    provider_series_code: str


WGI_DIAGNOSTIC_SPECS: tuple[WgiDiagnosticSpec, ...] = tuple(
    WgiDiagnosticSpec(
        base_indicator_code=base_indicator_code,
        diagnostic_kind=kind,
        source_key=WGI_DIAGNOSTIC_SOURCE_KEY,
        provider_source_code=WGI_DIAGNOSTIC_PROVIDER_SOURCE_CODE,
        provider_series_code=f"{_DIMENSION_SERIES_PREFIX[base_indicator_code]}{suffix}",
    )
    for base_indicator_code in WGI_BASE_INDICATORS
    for kind, suffix in _KIND_SUFFIX.items()
)


def get_wgi_diagnostic_specs(base_indicator_code: str) -> tuple[WgiDiagnosticSpec, ...]:
    """The three specs (LB, UB, SR) for one WGI base indicator."""
    return tuple(
        spec
        for spec in WGI_DIAGNOSTIC_SPECS
        if spec.base_indicator_code == base_indicator_code
    )


def validate_wgi_diagnostic_specs() -> None:
    """Structural invariants of the registry. Raises ValueError on violation.

    - exactly 9 specs (3 base indicators x 3 kinds, LB/UB/SR only)
    - no duplicate (base indicator, kind) identities
    - exactly one provider series per (base indicator, kind)
    - provider source identity explicit on every spec
    """
    if len(WGI_DIAGNOSTIC_SPECS) != 9:
        raise ValueError(
            f"Expected 9 WGI diagnostic specs (3 indicators x 3 kinds), "
            f"got {len(WGI_DIAGNOSTIC_SPECS)}"
        )
    seen: set[tuple[str, IndicatorDiagnosticKind]] = set()
    seen_series: set[str] = set()
    for spec in WGI_DIAGNOSTIC_SPECS:
        identity = (spec.base_indicator_code, spec.diagnostic_kind)
        if identity in seen:
            raise ValueError(f"Duplicate diagnostic identity: {identity}")
        seen.add(identity)
        if spec.provider_series_code in seen_series:
            raise ValueError(
                f"Provider series {spec.provider_series_code!r} used by more "
                f"than one spec"
            )
        seen_series.add(spec.provider_series_code)
        if not spec.provider_source_code or not spec.source_key:
            raise ValueError(
                f"Spec {identity} must carry explicit provider source and "
                f"data-source identity"
            )
    kinds = {spec.diagnostic_kind for spec in WGI_DIAGNOSTIC_SPECS}
    if kinds != {
        IndicatorDiagnosticKind.ci_lower_bound,
        IndicatorDiagnosticKind.ci_upper_bound,
        IndicatorDiagnosticKind.source_count,
    }:
        raise ValueError(f"Unexpected diagnostic kinds in registry: {kinds}")