from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from datetime import datetime
from enum import Enum
from app.models.ingestion_run import IngestionRun, IngestionRunStatus

class IngestionRunBase(BaseModel):
    data_source_id: int
    status: IngestionRunStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    rows_received: int = 0
    rows_inserted: int = 0
    rows_skipped: int = 0
    rows_revised: int = 0
    error_count: int = 0
    errors: Optional[dict] = None
    run_metadata: Optional[dict] = None
    created_at: datetime

class IngestionRunCreate(IngestionRunBase):
    pass

class IngestionRun(IngestionRunBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
