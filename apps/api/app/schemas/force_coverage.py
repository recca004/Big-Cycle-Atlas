from datetime import date
from typing import List, Optional

from pydantic import BaseModel

from app.cycle.force_definitions import ForceCoverageStatus


class ForceInputRead(BaseModel):
    indicator_code: str
    name: Optional[str] = None
    has_data: bool
    has_source_series: bool
    source: Optional[str] = None
    latest_period: Optional[date] = None


class ForceCoverageRead(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    status: ForceCoverageStatus
    coverage_notes: Optional[str] = None
    live_inputs: List[ForceInputRead]
    candidate_inputs: List[ForceInputRead]


class ForceCoverageResponse(BaseModel):
    country: str
    forces: List[ForceCoverageRead]