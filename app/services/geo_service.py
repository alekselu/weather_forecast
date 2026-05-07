"""
GeoService: resolves city name → (latitude, longitude).

v0: in-memory cache + geopy (Nominatim).
v1+: cache persisted to PostgreSQL geo_cache table.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from app.core.exceptions import CityNotFoundError
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class GeoLocation:
    city: str
    latitude: float
    longitude: float


class GeoService:
    """
    Resolves city names to geographic coordinates.

    Caches results in-memory to avoid repeated geocoding calls.
    Raises CityNotFoundError for unknown/unresolvable cities.
    """

    # Built-in known cities to avoid geocoding in tests / offline mode
    _KNOWN_CITIES: Dict[str, GeoLocation] = {
        "saint petersburg": GeoLocation("Saint Petersburg", 59.9343, 30.3351),
        "moscow": GeoLocation("Moscow", 55.7558, 37.6173),
        "novosibirsk": GeoLocation("Novosibirsk", 54.9884, 82.9375),
        "ekaterinburg": GeoLocation("Ekaterinburg", 56.8389, 60.6057),
        "kazan": GeoLocation("Kazan", 55.7964, 49.1089),
    }

    def __init__(self, use_geocoder: bool = True) -> None:
        self._cache: Dict[str, GeoLocation] = {}
        self._use_geocoder = use_geocoder

    def resolve(self, city: str) -> GeoLocation:
        """
        Resolve city to coordinates.
        Lookup order: in-memory cache → built-in list → Nominatim geocoder.
        """
        key = city.strip().lower()

        # 1. In-memory cache
        if key in self._cache:
            return self._cache[key]

        # 2. Built-in known cities
        if key in self._KNOWN_CITIES:
            loc = self._KNOWN_CITIES[key]
            self._cache[key] = loc
            return loc

        # 3. Geocoder (optional, may be disabled in tests)
        if self._use_geocoder:
            loc = self._geocode(city)
            self._cache[key] = loc
            return loc

        raise CityNotFoundError(city)

    def _geocode(self, city: str) -> GeoLocation:
        """Call Nominatim via geopy. Raises CityNotFoundError on failure."""
        try:
            from geopy.geocoders import Nominatim
            from geopy.exc import GeocoderServiceError, GeocoderTimedOut

            geolocator = Nominatim(user_agent="weather-forecast-app/0.1")
            location = geolocator.geocode(city, timeout=5)

            if location is None:
                raise CityNotFoundError(city)

            result = GeoLocation(
                city=city,
                latitude=round(location.latitude, 4),
                longitude=round(location.longitude, 4),
            )
            logger.info(
                "geocoded_city",
                city=city,
                lat=result.latitude,
                lon=result.longitude,
            )
            return result

        except CityNotFoundError:
            raise
        except Exception as exc:
            logger.warning("geocoder_failed", city=city, error=str(exc))
            raise CityNotFoundError(city) from exc


# Module-level singleton
_geo_service = GeoService()


def get_geo_service() -> GeoService:
    return _geo_service
