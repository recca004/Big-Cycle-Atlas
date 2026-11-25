"""Historical execution modes (Mission 4 §23).

Explicit, non-interchangeable modes for how historical evaluation selects
observations. These are SEPARATE concepts:

- observation period        — the economic period the value describes
- release_date              — when the provider actually published the value
- retrieved_at              — when the Atlas ingested it (NOT publication
                              evidence and never used as such)
- evaluation cutoff         — the as-of moment a historical evaluation
                              claims to know about

Modes:
- CURRENT_LATEST: latest-vintage, period-complete selection. The standard
  production path — NOT a backtest, merely current-state computation.
- RETROSPECTIVE_LATEST_VINTAGE: identical selection semantics used for
  LOOKING BACK. Explicitly named so a retrospective curve can never be
  confused with a strict as-of reconstruction.
- STRICT_AS_OF: only observations with provider release evidence
  (release_date IS NOT NULL) published at/before the information cutoff
  are eligible; revisions published after the cutoff are excluded. Rows
  without release evidence are ineligible — never silently included.
- RESEARCH_ASSUMPTION: eligibility from estimated provider release lags
  (period_end + assumed lag <= cutoff). These lags are documented research
  assumptions, NOT verified publication dates.

`backtest_safe` may only be True when a value was produced under
STRICT_AS_OF with verified release evidence on every required input —
the existence of the mode does not make results safe.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class ExecutionMode(str, Enum):
    CURRENT_LATEST = "current_latest"
    RETROSPECTIVE_LATEST_VINTAGE = "retrospective_latest_vintage"
    STRICT_AS_OF = "strict_as_of"
    RESEARCH_ASSUMPTION = "research_assumption"


@dataclass(frozen=True)
class ExecutionSpec:
    """How a historical evaluation may select information."""

    mode: ExecutionMode
    # Information cutoff — everything the evaluation is allowed to know
    # must be published at/before this date. Required for strict and
    # research-assumption modes; ignored by latest-vintage modes.
    info_cutoff: date | None = None

    def __post_init__(self) -> None:
        if self.mode in (
            ExecutionMode.STRICT_AS_OF,
            ExecutionMode.RESEARCH_ASSUMPTION,
        ) and self.info_cutoff is None:
            raise ValueError(
                f"{self.mode.value} requires an information cutoff date"
            )

    @property
    def is_strict(self) -> bool:
        return self.mode is ExecutionMode.STRICT_AS_OF


# Retrospective default — used when callers do not pass an explicit spec.
# Explicitly NOT strict: callers must opt in and supply a cutoff.
RETROSPECTIVE_SPEC = ExecutionSpec(
    mode=ExecutionMode.RETROSPECTIVE_LATEST_VINTAGE
)


def parse_execution_spec(
    mode: str | None, info_cutoff: date | None
) -> ExecutionSpec:
    """Validate API-layer execution parameters into an ExecutionSpec.

    Defaults to retrospective latest-vintage. Raises ValueError on an
    unknown mode or a strict/assumption request without a cutoff — callers
    (routes) map that to 422."""
    if mode is None:
        return RETROSPECTIVE_SPEC
    try:
        parsed = ExecutionMode(mode)
    except ValueError:
        valid = ", ".join(m.value for m in ExecutionMode)
        raise ValueError(
            f"unknown execution_mode {mode!r} (valid: {valid})"
        ) from None
    return ExecutionSpec(mode=parsed, info_cutoff=info_cutoff)
