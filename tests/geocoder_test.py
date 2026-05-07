# geocoder_test.py
import pytest
from unittest.mock import AsyncMock
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from app.utils.geolocation import GeoCoder


@pytest.mark.asyncio
async def test_fetch_location_success():
    coder = GeoCoder()
    loc = type("Loc", (), {"latitude": 55.7558, "longitude": 37.6176})()

    coder._ratelimiter = AsyncMock(return_value=loc)

    lat, lon = await coder.fetch_location("Moscow", country_code="ru")

    assert lat == 55.7558
    assert lon == 37.6176
    coder._ratelimiter.assert_awaited_once_with("Moscow", country_codes="ru")


@pytest.mark.asyncio
async def test_fetch_location_not_found():
    coder = GeoCoder()
    coder._ratelimiter = AsyncMock(return_value=None)

    with pytest.raises(ValueError) as exc_info:
        await coder.fetch_location("NonExistentCity")

    assert "Could not geocode 'NonExistentCity'" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_location_timeout():
    coder = GeoCoder()
    coder._ratelimiter = AsyncMock(side_effect=GeocoderTimedOut("Timeout"))

    with pytest.raises(RuntimeError) as exc_info:
        await coder.fetch_location("Moscow")

    assert "timed out" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_fetch_location_unavailable():
    coder = GeoCoder()
    coder._ratelimiter = AsyncMock(side_effect=GeocoderUnavailable("Service down"))

    with pytest.raises(RuntimeError) as exc_info:
        await coder.fetch_location("Moscow")

    assert "unavailable" in str(exc_info.value).lower()
