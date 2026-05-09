from geopy.geocoders import Nominatim
from geopy.adapters import AioHTTPAdapter
from geopy.extra.rate_limiter import AsyncRateLimiter
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable, GeocoderServiceError
from app.core.exceptions import CityNotFoundError


class GeoCoder:
    def __init__(self, request_delay: float = 1):
        self._user_agent = (
            "WeatherPredictorForCities (https://github.com/alekselu/weather_forecast)"
        )
        self._geolocator = Nominatim(
            user_agent=self._user_agent,
            adapter_factory=AioHTTPAdapter,
        )
        self._ratelimiter = AsyncRateLimiter(
            self._geolocator.geocode,
            min_delay_seconds=request_delay,
        )

    async def fetch_location(
        self, city: str, country_code: str = "ru"
    ) -> tuple[float, float]:
        try:
            loc = await self._ratelimiter(city, country_codes=country_code)
        except GeocoderTimedOut:
            raise RuntimeError(
                "Nominatim timed out – too many requests or server overload"
            )
        except GeocoderUnavailable:
            raise RuntimeError(
                "Nominatim is unavailable – possibly rate-limited or blocked"
            )
        except GeocoderServiceError as e:
            raise RuntimeError(f"Nominatim service error: {e}")
        if loc is None:
            raise CityNotFoundError(f"Could not geocode {city!r}")
        return loc.latitude, loc.longitude


# Module-level singleton
_geo_coder = GeoCoder()


def get_geo_coder() -> GeoCoder:
    return _geo_coder
