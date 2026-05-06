# geocoder_test.py
import pytest
from unittest.mock import AsyncMock

from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from app.utils.geolocation import GeoCoder, Direction, Coordinates, Place


@pytest.mark.asyncio
async def test_fetch_location_from_success():
    coder = GeoCoder()
    loc = type("Loc", (), {"latitude": 55.7558, "longitude": 37.6176})()

    coder._fetch_location_by = AsyncMock(return_value=loc)
    place = Place("Moscow", "city", "ru")

    coords: Coordinates = await coder.fetch_location_from(place)

    assert coords.latitude == 55.7558
    assert coords.longitude == 37.6176

    coder._fetch_location_by.assert_awaited_once_with(
        direction=Direction.FROM,
        query={
            "city": "Moscow",
            "countrycodes": "ru",
        },
        exactly_one=True,
    )


@pytest.mark.asyncio
async def test_fetch_location_from_not_found():
    coder = GeoCoder()
    coder._fetch_location_by = AsyncMock(return_value=None)

    with pytest.raises(AttributeError):
        await coder.fetch_location_from(Place("NonExistentCity"))

    coder._fetch_location_by.assert_awaited_once_with(
        direction=Direction.FROM,
        query={
            "city": "NonExistentCity",
            "countrycodes": "ru",
        },
        exactly_one=True,
    )


@pytest.mark.asyncio
async def test_fetch_location_from_timeout():
    coder = GeoCoder()
    coder._fetch_location_by = AsyncMock(side_effect=GeocoderTimedOut("Timeout"))

    place = Place("Moscow")

    with pytest.raises(GeocoderTimedOut) as exc_info:
        await coder.fetch_location_from(place)

    assert "Timeout" in str(exc_info.value)

    coder._fetch_location_by.assert_awaited_once_with(
        direction=Direction.FROM,
        query={
            "city": "Moscow",
            "countrycodes": "ru",
        },
        exactly_one=True,
    )


@pytest.mark.asyncio
async def test_fetch_location_from_unavailable():
    coder = GeoCoder()
    coder._fetch_location_by = AsyncMock(
        side_effect=GeocoderUnavailable("Service down")
    )

    place = Place("Moscow")

    with pytest.raises(GeocoderUnavailable) as exc_info:
        await coder.fetch_location_from(place)

    assert "Service down" in str(exc_info.value)

    coder._fetch_location_by.assert_awaited_once_with(
        direction=Direction.FROM,
        query={
            "city": "Moscow",
            "countrycodes": "ru",
        },
        exactly_one=True,
    )


@pytest.mark.asyncio
async def test_fetch_location_to_success():
    coder = GeoCoder()

    loc = type(
        "Loc",
        (),
        {
            "raw": {
                "address": {
                    "city": "Moscow",
                    "country_code": "ru",
                }
            }
        },
    )()

    coder._fetch_location_by = AsyncMock(return_value=loc)

    place: Place = await coder.fetch_location_to(55.7558, 37.6176)

    assert place.name == "Moscow"
    assert place.country_code == "ru"

    assert place.type == "city"

    coder._fetch_location_by.assert_awaited_once_with(
        direction=Direction.TO,
        query=(55.7558, 37.6176),
        exactly_one=True,
        addressdetails=True,
    )


@pytest.mark.asyncio
async def test_fetch_location_to_missing_city_raises_value_error():
    coder = GeoCoder()

    loc = type(
        "Loc",
        (),
        {
            "raw": {
                "address": {
                    "country_code": "ru",
                }
            }
        },
    )()

    coder._fetch_location_by = AsyncMock(return_value=loc)

    with pytest.raises(ValueError) as exc_info:
        await coder.fetch_location_to(55.7558, 37.6176)

    assert "Could not extract place from address" in str(exc_info.value)


@pytest.mark.asyncio
async def test_fetch_location_to_missing_country_code_raises_value_error():
    coder = GeoCoder()

    loc = type(
        "Loc",
        (),
        {
            "raw": {
                "address": {
                    "city": "Moscow",
                }
            }
        },
    )()

    coder._fetch_location_by = AsyncMock(return_value=loc)

    with pytest.raises(ValueError) as exc_info:
        await coder.fetch_location_to(55.7558, 37.6176)

    assert "Could not extract country code from address" in str(exc_info.value)
