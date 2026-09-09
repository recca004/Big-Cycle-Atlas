from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.source_series import SourceSeries

class SourceSeriesBase(BaseModel):
    data_source_id: int
    indicator_id: int
    external_code: str
    external_name: Optional[str] = None
    external_unit: Optional[str] = None
    country_scope: Optional[str] = None
    transform_notes: Optional[str] = None
    is_active: bool = True

class SourceSeriesCreate(SourceSeriesBase):
    pass

class SourceSeries(SourceSeriesBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
