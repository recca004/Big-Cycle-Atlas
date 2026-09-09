"""Offline tests for the WID adapter (Sprint 5.20 Part B).

Uses a tiny in-memory zip fixture — no 882 MB download in pytest.
"""
import io
import math
import zipfile
from datetime import date, datetime, timezone

import pytest
import asyncio

from app.data_sources.base import DataSourceError, DataSourceParseError, SeriesMappingError
from app.data_sources.wid import WidAdapter
from app.data_sources.wid_mappings import WID_COUNTRY_BY_ISO3, get_wid_mapping_by_external_code

WEALTH_CODE = "WID/shwealj992/p90p100"
RETRIEVED_AT = datetime(2026, 9, 10, 12, 0, 0, tzinfo=timezone.utc)


def _make_zip(country_code: str, rows: list[dict]) -> bytes:
    """Build a tiny zip with one WID CSV file."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        lines = ["country;variable;percentile;year;value;age;pop;data_quality"]
        for r in rows:
            lines.append(
                f"{r['country']};{r['variable']};{r['percentile']};{r['year']};"
                f"{r['value']};{r['age']};{r['pop']};{r.get('data_quality', '')}"
            )
        zf.writestr(f"WID_data_{country_code}.csv", "\n".join(lines))
    return buf.getvalue()


def _make_adapter(zip_bytes: bytes, tmp_path) -> WidAdapter:
    zip_path = tmp_path / "wid_test.zip"
    zip_path.write_bytes(zip_bytes)
    return WidAdapter(zip_path=zip_path, retrieved_at=RETRIEVED_AT)


def _wealth_row(country: str, year: int, value: str, dq: str = "0") -> dict:
    return {
        "country": country,
        "variable": "shwealj992",
        "percentile": "p90p100",
        "year": str(year),
        "value": value,
        "age": "992",
        "pop": "j",
        "data_quality": dq,
    }


async def test_exact_series_identity(tmp_path):
    """Only shwealj992/p90p100 rows are extracted — other variables/percentiles skipped."""
    rows = [
        _wealth_row("US", 2020, "0.72"),
        _wealth_row("US", 2021, "0.73"),
        # Wrong variable — should be skipped
        {**_wealth_row("US", 2020, "0.50"), "variable": "shweali992"},
        # Wrong percentile — should be skipped
        {**_wealth_row("US", 2020, "0.50"), "percentile": "p99p100"},
        # Wrong pop — should be skipped
        {**_wealth_row("US", 2020, "0.50"), "pop": "i"},
    ]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    observations = await adapter.fetch_indicator("USA", WEALTH_CODE)
    assert len(observations) == 2
    assert [o.period for o in observations] == [2020, 2021]
    assert observations[0].value == 0.72
    assert observations[0].indicator_code == "WEALTH_SHARE_TOP_10"
    assert observations[0].source_key == "wid"
    assert observations[0].unit == "share (0-1)"


async def test_iso3_to_iso2_country_isolation(tmp_path):
    """Each country file is isolated — USA reads only US file."""
    rows = [_wealth_row("US", 2020, "0.72")]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    observations = await adapter.fetch_indicator("USA", WEALTH_CODE)
    assert len(observations) == 1
    assert observations[0].country_iso3 == "USA"


async def test_wrong_country_in_row_rejected(tmp_path):
    """A row with a different country code raises — no cross-country leakage."""
    rows = [
        _wealth_row("CN", 2020, "0.41"),  # CN row in US file
    ]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    with pytest.raises(DataSourceParseError, match="country"):
        await adapter.fetch_indicator("USA", WEALTH_CODE)


async def test_missing_value_skipped(tmp_path):
    """Empty value is skipped — never zero-filled."""
    rows = [
        _wealth_row("US", 2020, "0.72"),
        {**_wealth_row("US", 2021, ""), },
        _wealth_row("US", 2022, "0.74"),
    ]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    observations = await adapter.fetch_indicator("USA", WEALTH_CODE)
    assert [o.period for o in observations] == [2020, 2022]


async def test_zero_is_legitimate_value(tmp_path):
    """A provider zero is a real value, not missing."""
    rows = [_wealth_row("US", 2020, "0")]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    observations = await adapter.fetch_indicator("USA", WEALTH_CODE)
    assert len(observations) == 1
    assert observations[0].value == 0.0


async def test_finite_validation_rejects_nan(tmp_path):
    rows = [_wealth_row("US", 2020, "NaN")]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    with pytest.raises(DataSourceParseError, match="not finite"):
        await adapter.fetch_indicator("USA", WEALTH_CODE)


async def test_finite_validation_rejects_inf(tmp_path):
    rows = [_wealth_row("US", 2020, "Infinity")]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    with pytest.raises(DataSourceParseError, match="not finite"):
        await adapter.fetch_indicator("USA", WEALTH_CODE)


async def test_range_validation_rejects_negative(tmp_path):
    rows = [_wealth_row("US", 2020, "-0.1")]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    with pytest.raises(DataSourceParseError, match="out of range"):
        await adapter.fetch_indicator("USA", WEALTH_CODE)


async def test_range_validation_rejects_above_one(tmp_path):
    rows = [_wealth_row("US", 2020, "1.5")]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    with pytest.raises(DataSourceParseError, match="out of range"):
        await adapter.fetch_indicator("USA", WEALTH_CODE)


async def test_data_quality_preserved_in_raw_payload(tmp_path):
    """data_quality is preserved but NOT used for filtering.

    Sprint 5.20.1: both the raw provider string (data_quality_raw) and the
    typed convenience value (data_quality) are preserved. The raw string
    is never lost — even for unknown codes.
    """
    rows = [
        _wealth_row("US", 2020, "0.72", dq="0"),
        _wealth_row("US", 2021, "0.73", dq="1"),
        _wealth_row("US", 2022, "0.74", dq="2"),
    ]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    observations = await adapter.fetch_indicator("USA", WEALTH_CODE)
    # ALL rows imported — no filtering (official semantics unverified)
    assert len(observations) == 3
    assert observations[0].raw_payload["data_quality"] == 0
    assert observations[1].raw_payload["data_quality"] == 1
    assert observations[2].raw_payload["data_quality"] == 2
    # Raw provider representation preserved exactly
    assert observations[0].raw_payload["data_quality_raw"] == "0"
    assert observations[1].raw_payload["data_quality_raw"] == "1"
    assert observations[2].raw_payload["data_quality_raw"] == "2"


async def test_data_quality_raw_preserved_for_unknown_code(tmp_path):
    """An unknown data_quality code (e.g. 'A') is preserved as the raw
    string; the typed value is None; the observation is NOT filtered."""
    rows = [
        _wealth_row("US", 2020, "0.72", dq="0"),
        _wealth_row("US", 2021, "0.73", dq="A"),
    ]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    observations = await adapter.fetch_indicator("USA", WEALTH_CODE)
    assert len(observations) == 2  # no row filtered
    assert observations[0].raw_payload["data_quality_raw"] == "0"
    assert observations[0].raw_payload["data_quality"] == 0
    assert observations[1].raw_payload["data_quality_raw"] == "A"
    assert observations[1].raw_payload["data_quality"] is None


async def test_data_quality_raw_preserved_for_empty_string(tmp_path):
    """An empty data_quality string is preserved as '' and typed as None."""
    rows = [
        _wealth_row("US", 2020, "0.72", dq=""),
    ]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    observations = await adapter.fetch_indicator("USA", WEALTH_CODE)
    assert len(observations) == 1
    assert observations[0].raw_payload["data_quality_raw"] == ""
    assert observations[0].raw_payload["data_quality"] is None


async def test_raw_payload_provenance(tmp_path):
    rows = [_wealth_row("US", 2020, "0.72", dq="0")]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    observations = await adapter.fetch_indicator("USA", WEALTH_CODE)
    rp = observations[0].raw_payload
    assert rp["provider_country"] == "US"
    assert rp["variable"] == "shwealj992"
    assert rp["percentile"] == "p90p100"
    assert rp["age"] == "992"
    assert rp["pop"] == "j"
    assert rp["data_quality_raw"] == "0"
    assert rp["data_quality"] == 0
    assert rp["value"] == "0.72"


async def test_unknown_country_raises(tmp_path):
    rows = [_wealth_row("US", 2020, "0.72")]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    with pytest.raises(DataSourceError, match="ISO2 mapping"):
        await adapter.fetch_indicator("BRA", WEALTH_CODE)


async def test_unmapped_external_code_raises(tmp_path):
    rows = [_wealth_row("US", 2020, "0.72")]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    with pytest.raises(SeriesMappingError):
        await adapter.fetch_indicator("USA", "WID/unknown")


async def test_missing_zip_file_raises(tmp_path):
    adapter = WidAdapter(zip_path=tmp_path / "nonexistent.zip", retrieved_at=RETRIEVED_AT)
    with pytest.raises(DataSourceError, match="not found"):
        await adapter.fetch_indicator("USA", WEALTH_CODE)


async def test_missing_country_file_raises(tmp_path):
    # Zip exists but has no WID_data_US.csv
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("WID_data_CN.csv", "country;variable;percentile;year;value;age;pop;data_quality\n")
    zip_path = tmp_path / "wid_test.zip"
    zip_path.write_bytes(buf.getvalue())
    adapter = WidAdapter(zip_path=zip_path, retrieved_at=RETRIEVED_AT)
    with pytest.raises(DataSourceError, match="no file"):
        await adapter.fetch_indicator("USA", WEALTH_CODE)


def test_all_tracked_8_countries_resolvable():
    """All 8 tracked countries have ISO3→ISO2 mappings."""
    expected = {"USA": "US", "CHN": "CN", "CHE": "CH", "DEU": "DE",
                "FRA": "FR", "GBR": "GB", "JPN": "JP", "IND": "IN"}
    for iso3, iso2 in expected.items():
        assert WID_COUNTRY_BY_ISO3[iso3] == iso2


async def test_start_end_year_filter(tmp_path):
    rows = [
        _wealth_row("US", 2018, "0.70"),
        _wealth_row("US", 2019, "0.71"),
        _wealth_row("US", 2020, "0.72"),
        _wealth_row("US", 2021, "0.73"),
        _wealth_row("US", 2022, "0.74"),
    ]
    zip_bytes = _make_zip("US", rows)
    adapter = _make_adapter(zip_bytes, tmp_path)
    observations = await adapter.fetch_indicator("USA", WEALTH_CODE, start_year=2019, end_year=2021)
    assert [o.period for o in observations] == [2019, 2020, 2021]
