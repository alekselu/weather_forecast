# geocoder_test.py
import pytest
from unittest.mock import AsyncMock

from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from app.utils.geolocation import GeoCoder, Direction


@pytest.mark.asyncio
async def test_fetch_location_from_success():
    coder = GeoCoder()
    loc = type("Loc", (), {"latitude": 55.7558, "longitude": 37.6176})()

    coder._fetch_location_by = AsyncMock(return_value=loc)

    lat, lon = await coder.fetch_location_from("Moscow", country_code="ru")

    assert lat == 55.7558
    assert lon == 37.6176

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
        await coder.fetch_location_from("NonExistentCity")

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

    with pytest.raises(GeocoderTimedOut) as exc_info:
        await coder.fetch_location_from("Moscow")

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

    with pytest.raises(GeocoderUnavailable) as exc_info:
        await coder.fetch_location_from("Moscow")

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

    city, country_code = await coder.fetch_location_to(55.7558, 37.6176)

    assert city == "Moscow"
    assert country_code == "ru"

    coder._fetch_location_by.assert_awaited_once_with(
        direction=Direction.TO,
        query=(55.7558, 37.6176),
        exactly_one=True,
        addressdetails=True,
    )


@pytest.mark.asyncio
async def test_fetch_location_to_uses_town_if_city_missing():
    coder = GeoCoder()

    loc = type(
        "Loc",
        (),
        {
            "raw": {
                "address": {
                    "town": "SomeTown",
                    "country_code": "ru",
                }
            }
        },
    )()

    coder._fetch_location_by = AsyncMock(return_value=loc)

    city, country_code = await coder.fetch_location_to(10.0, 20.0)

    assert city == "SomeTown"
    assert country_code == "ru"


@pytest.mark.asyncio
async def test_fetch_location_to_uses_village_if_city_and_town_missing():
    coder = GeoCoder()

    loc = type(
        "Loc",
        (),
        {
            "raw": {
                "address": {
                    "village": "SomeVillage",
                    "country_code": "ru",
                }
            }
        },
    )()

    coder._fetch_location_by = AsyncMock(return_value=loc)

    city, country_code = await coder.fetch_location_to(10.0, 20.0)

    assert city == "SomeVillage"
    assert country_code == "ru"


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

    assert "Could not extract city from address" in str(exc_info.value)


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
