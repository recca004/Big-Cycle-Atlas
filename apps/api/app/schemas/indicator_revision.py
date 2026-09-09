from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.indicator_revision import IndicatorRevision

class IndicatorRevisionBase(BaseModel):
    prior_observation_id: Optional[int] = None
    new_observation_id: int
    revision_date: datetime
    old_value: Optional[float] = None
    new_value: float
    delta: Optional[float] = None

class IndicatorRevisionCreate(IndicatorRevisionBase):
    pass

class IndicatorRevision(IndicatorRevisionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
