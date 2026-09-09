from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.observation import Observation

class ObservationBase(BaseModel):
    country_id: int
    indicator_id: int
    data_source_id: int
    source_series_id: int
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    value: float
    unit: Optional[str] = None
    observation_date: datetime
    release_date: Optional[datetime] = None
    retrieved_at: datetime
    vintage_number: int = 1
    supersedes_observation_id: Optional[int] = None
    raw_payload: Optional[dict] = None
    source_key: Optional[str] = None

class ObservationCreate(ObservationBase):
    pass

class Observation(ObservationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    indicator_code: Optional[str] = None
    source_key: Optional[str] = None
