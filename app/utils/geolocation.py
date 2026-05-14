from __future__ import annotations

from enum import Enum
from functools import partial
from dataclasses import dataclass
from geopy.adapters import AioHTTPAdapter
from geopy.exc import GeocoderServiceError, GeocoderTimedOut, GeocoderUnavailable
from geopy.extra.rate_limiter import AsyncRateLimiter
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError
from app.core.exceptions import CityNotFoundError
from geopy.geocoders import Nominatim
from geopy.location import Location
from app.utils.structures import City, Coordinates


class Direction(Enum):
    FROM = 1
    TO = 2


async def _process_function_by(from_func, to_func, direction: Direction, **kwargs):
    match direction:
        case Direction.FROM:
            return await from_func(**kwargs)
        case Direction.TO:
            return await to_func(**kwargs)
        case _:
            raise ValueError("Unsupported Enum Value")


class GeoCoder:
    def __init__(self, request_delay: float = 1):
        self._user_agent = (
            "WeatherPredictorForCities "
            "(https://github.com/alekselu/weather_forecast)"
        )

        self._geolocator = Nominatim(
            user_agent=self._user_agent,
            adapter_factory=AioHTTPAdapter,
        )

        self._process = partial(
            _process_function_by,
            from_func=self._geolocator.geocode,
            to_func=self._geolocator.reverse,
        )

        self._ratelimiter = AsyncRateLimiter(
            self._process,
            min_delay_seconds=request_delay,
        )

    async def _fetch_location_by(self, direction: Direction, **kwargs) -> Location:
        try:
            loc = await self._ratelimiter(direction=direction, **kwargs)
        except GeocoderTimedOut as e:
            raise RuntimeError(
                "Nominatim timed out – too many requests or server overload"
            ) from e
        except GeocoderUnavailable as e:
            raise RuntimeError(
                "Nominatim is unavailable – possibly rate-limited or blocked"
            ) from e
        except GeocoderServiceError as e:
            raise RuntimeError(f"Nominatim service error: {e}") from e

        if loc is None:
            raise ValueError(f"Could not resolve location from arguments: {kwargs!r}")

        return loc

    async def fetch_location_from(
        self,
        place: City,
    ) -> Coordinates:
        loc: Location = await self._fetch_location_by(
            direction=Direction.FROM,
            query={
                "city": place.name,
                "country_code": place.country_code,
            },
            exactly_one=True,
        )

        return Coordinates(float(loc.latitude), float(loc.longitude))

    @staticmethod
    def _extract_city_and_country_code(location: Location | None) -> City:
        if location is None:
            raise ValueError("Got empty location")

        address = location.raw.get("address", {})
        place_name = address.get("city", None)
        country_code = address.get("country_code")

        if not place_name:
            raise ValueError(f"Could not extract place from address: {address!r}")

        if not country_code:
            raise ValueError(
                f"Could not extract country code from address: {address!r}"
            )

        return City(
            name=place_name,
            country_code=country_code,
        )

    async def fetch_location_to(self, coords: Coordinates) -> City:
        loc: Location = await self._fetch_location_by(
            direction=Direction.TO,
            query=(coords.latitude, coords.longitude),
            exactly_one=True,
            addressdetails=True,
            language="en",
        )

        return self._extract_city_and_country_code(loc)


# Module-level singleton
_geo_coder = GeoCoder()


def get_geo_coder() -> GeoCoder:
    return _geo_coder
