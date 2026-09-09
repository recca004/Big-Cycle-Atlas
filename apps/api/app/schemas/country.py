from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CountryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    iso3: str
    iso2: str
    name: str
    region: str
    created_at: datetime
    updated_at: datetime
    observation_count: Optional[int] = None
    indicator_count: Optional[int] = None
    latest_observation_year: Optional[int] = None