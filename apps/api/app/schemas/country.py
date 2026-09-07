from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CountryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    iso3: str
    iso2: str
    name: str
    region: str
    created_at: datetime
    updated_at: datetime