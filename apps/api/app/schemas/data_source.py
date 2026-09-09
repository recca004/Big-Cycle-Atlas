from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.data_source import DataSource, DataSourceStatus

class DataSourceBase(BaseModel):
    key: str
    name: str
    base_url: Optional[str] = None
    auth_type: Optional[str] = None
    status: DataSourceStatus
    update_frequency: Optional[str] = None
    documentation_url: Optional[str] = None

class DataSourceCreate(DataSourceBase):
    pass

class DataSource(DataSourceBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
    extra_metadata: Optional[dict] = None
