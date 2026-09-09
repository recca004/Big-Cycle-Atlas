from abc import ABC, abstractmethod
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel


class DataSourceError(Exception):
    """Base error for data source connector failures."""


class DataSourceHTTPError(DataSourceError):
    """Network or API failure (non-200 response)."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class DataSourceParseError(DataSourceError):
    """Response was received but could not be parsed into the expected format."""


class SeriesMappingError(DataSourceError):
    """External series code has no mapping to a canonical Big Cycle Atlas indicator.

    Raised instead of guessing an indicator code, so unmapped series can never
    be silently persisted under a wrong identity.
    """


class DataSourceNoDataError(DataSourceError):
    """The source clearly reports that no observations exist for this request.

    Distinct from transport/parse failures: a known no-coverage country/series
    is not an ingestion outage, so callers record a clean no-data outcome
    instead of a failed run. Raised only on an unambiguous source signal
    (e.g. OECD's 404 'NoRecordsFound' body).
    """


class ObservationDTO(BaseModel):
    """Normalized observation returned by an adapter. Not persisted directly."""

    country_iso3: str
    indicator_code: str
    external_series_code: str
    period: int  # year
    value: float
    unit: Optional[str] = None
    source_key: str
    observation_date: date
    release_date: Optional[datetime] = None
    retrieved_at: datetime
    raw_payload: dict[str, Any]


class BaseDataSourceAdapter(ABC):
    """Contract for external data source connectors.

    Each adapter fetches from its external API, parses the source-specific
    response, and returns normalized ObservationDTO objects. Persistence is
    handled elsewhere.
    """

    source_key: str

    @abstractmethod
    async def fetch_indicator(
        self,
        country_iso3: str,
        external_series_code: str,
        start_year: int | None = None,
        end_year: int | None = None,
    ) -> list[ObservationDTO]:
        """Fetch one indicator series for one country as normalized DTOs."""