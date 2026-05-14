# geocoder_test.py
import pytest
from unittest.mock import AsyncMock
from dataclasses import astuple
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

from app.utils.geolocation import GeoCoder, Direction
from app.utils.structures import City, Coordinates

TEST_CASES = [
    (City("Berlin", "de"), Coordinates(52.52, 13.40)),
    (City("Cotswold", "gb"), Coordinates(51.85, -1.89)),
    (City("Moscow", "ru"), Coordinates(55.75, 37.62)),
]


def ids(x: tuple[City, Coordinates]):
    return f"{x[0].name}_{x[0].country_code}_to_{x[1].latitude}_{x[1].longitude}"


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("case", TEST_CASES, ids=ids)
async def test_fetch_location_from_real_api(case):
    coder = GeoCoder()
    place = case[0]
    coords = case[1]
    location = await coder.fetch_location_from(place)

    assert location is not None
    assert round(location.latitude, 2) == coords.latitude
    assert round(location.longitude, 2) == coords.longitude


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.parametrize("case", TEST_CASES, ids=ids)
async def test_fetch_location_to_real_api(case):
    coder = GeoCoder()
    place = case[0]
    coords = case[1]
    location = await coder.fetch_location_to(coords)

    assert location is not None
    assert place.name in location.name
    assert place.country_code == location.country_code


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fetch_location_from_real_api_missing_city_raises_value_error():
    coder = GeoCoder()

    place = City(
        name="DefinitelyNotARealCityName123456789",
        country_code="de",
    )

    with pytest.raises(ValueError):
        await coder.fetch_location_from(place)


@pytest.mark.component
@pytest.mark.asyncio
async def test_fetch_location_from_success():
    coder = GeoCoder()
    loc = type("Loc", (), {"latitude": 55.7558, "longitude": 37.6176})()

    coder._fetch_location_by = AsyncMock(return_value=loc)
    place = City("Moscow", "ru")

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


@pytest.mark.component
@pytest.mark.asyncio
async def test_fetch_location_from_not_found():
    coder = GeoCoder()
    coder._fetch_location_by = AsyncMock(return_value=None)

    with pytest.raises(AttributeError):
        await coder.fetch_location_from(City("NonExistentCity"))

    coder._fetch_location_by.assert_awaited_once_with(
        direction=Direction.FROM,
        query={
            "city": "NonExistentCity",
            "countrycodes": "ru",
        },
        exactly_one=True,
    )


@pytest.mark.component
@pytest.mark.asyncio
async def test_fetch_location_from_timeout():
    coder = GeoCoder()
    coder._fetch_location_by = AsyncMock(side_effect=GeocoderTimedOut("Timeout"))

    place = City("Moscow")

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


@pytest.mark.component
@pytest.mark.asyncio
async def test_fetch_location_from_unavailable():
    coder = GeoCoder()
    coder._fetch_location_by = AsyncMock(
        side_effect=GeocoderUnavailable("Service down")
    )

    place = City("Moscow")

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


@pytest.mark.component
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

    place: City = await coder.fetch_location_to(Coordinates(55.7558, 37.6176))

    assert place.name == "Moscow"
    assert place.country_code == "ru"

    coder._fetch_location_by.assert_awaited_once_with(
        direction=Direction.TO,
        query=(55.7558, 37.6176),
        exactly_one=True,
        addressdetails=True,
        language="en",
    )


@pytest.mark.component
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
        await coder.fetch_location_to(Coordinates(55.7558, 37.6176))

    assert "Could not extract place from address" in str(exc_info.value)


@pytest.mark.component
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
        await coder.fetch_location_to(Coordinates(55.7558, 37.6176))

    assert "Could not extract country code from address" in str(exc_info.value)
