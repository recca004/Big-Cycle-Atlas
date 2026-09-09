from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.models.indicator import Indicator, IndicatorStrengthDirection

class IndicatorBase(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    frequency: Optional[str] = None
    strength_direction: IndicatorStrengthDirection

class IndicatorCreate(IndicatorBase):
    pass

class Indicator(IndicatorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime
