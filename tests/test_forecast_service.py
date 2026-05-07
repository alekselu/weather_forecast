"""Unit tests for ForecastService."""

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import CityNotFoundError, ModelNotAvailableError
from app.ml.model_registry import ModelRegistry, ModelStub
from app.services.forecast_service import ForecastService
from app.services.geo_service import GeoService


@pytest.fixture
def service(geo_service, model_registry):
    return ForecastService(geo_service=geo_service, model_registry=model_registry)


class TestForecastService:
    def test_returns_forecast_response(self, service):
        result = service.get_forecast("Moscow")
        assert result.city == "Moscow"
        assert isinstance(result.avg_temperature_c, float)
        assert result.model_version == "stub-v0"

    def test_default_date_is_tomorrow(self, service):
        result = service.get_forecast("Moscow")
        expected = date.today() + timedelta(days=1)
        assert result.date == expected

    def test_explicit_date(self, service):
        target = date(2026, 7, 15)
        result = service.get_forecast("Moscow", forecast_date=target)
        assert result.date == target

    def test_city_not_found_propagates(self, service):
        with pytest.raises(CityNotFoundError):
            service.get_forecast("NonexistentCity123")

    def test_model_unavailable_propagates(self, geo_service, empty_registry):
        svc = ForecastService(geo_service=geo_service, model_registry=empty_registry)
        with pytest.raises(ModelNotAvailableError):
            svc.get_forecast("Moscow")

    def test_summer_forecast_warmer_than_winter(self, service):
        jan = service.get_forecast("Saint Petersburg", forecast_date=date(2026, 1, 15))
        jul = service.get_forecast("Saint Petersburg", forecast_date=date(2026, 7, 15))
        assert jul.avg_temperature_c > jan.avg_temperature_c
