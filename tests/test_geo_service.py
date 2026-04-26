"""Модульные тесты для GeoService."""

import pytest

from app.core.exceptions import CityNotFoundError
from app.services.geo_service import GeoLocation, GeoService


class TestGeoServiceBuiltIn:
    """GeoService разрешает известные города без вызова внешнего геокодера."""

    def test_resolves_saint_petersburg(self):
        """Проверка разрешения Санкт-Петербурга."""
        svc = GeoService(use_geocoder=False)
        loc = svc.resolve("Saint Petersburg")
        assert isinstance(loc, GeoLocation)
        assert abs(loc.latitude - 59.9) < 0.5
        assert abs(loc.longitude - 30.3) < 0.5

    def test_resolves_case_insensitive(self):
        """Проверка нечувствительности к регистру."""
        svc = GeoService(use_geocoder=False)
        loc = svc.resolve("MOSCOW")
        assert loc.city == "Moscow"

    def test_resolves_with_extra_whitespace(self):
        """Проверка обработки лишних пробелов."""
        svc = GeoService(use_geocoder=False)
        loc = svc.resolve("  kazan  ")
        assert loc.city == "Kazan"

    def test_caches_result(self):
        """Проверка кэширования результатов."""
        svc = GeoService(use_geocoder=False)
        loc1 = svc.resolve("Moscow")
        loc2 = svc.resolve("Moscow")
        assert loc1 is loc2  # тот же объект из кэша

    def test_unknown_city_raises(self):
        """Проверка, что неизвестный город вызывает исключение."""
        svc = GeoService(use_geocoder=False)
        with pytest.raises(CityNotFoundError) as exc_info:
            svc.resolve("NonexistentCityXYZ")
        assert "NonexistentCityXYZ" in str(exc_info.value)

    def test_city_not_found_error_attributes(self):
        """Проверка атрибутов исключения CityNotFoundError."""
        svc = GeoService(use_geocoder=False)
        with pytest.raises(CityNotFoundError) as exc_info:
            svc.resolve("Atlantis")
        assert exc_info.value.city == "Atlantis"
