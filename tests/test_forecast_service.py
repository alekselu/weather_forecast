"""Unit tests for ForecastService."""

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest

from app.core.exceptions import CityNotFoundError, ModelNotAvailableError
from app.ml.model_registry import ModelRegistry, ModelStub
from app.services.forecast_service import ForecastService
from app.utils.geolocation import GeoCoder


@pytest.fixture
def service(geo_coder, model_registry):
    return ForecastService(geo_coder=geo_coder, model_registry=model_registry)


class TestForecastService:
    def test_returns_forecast_response(self, service):
        result = service.get_forecast("Moscow")
        assert result.city == "Moscow"
        assert isinstance(result.payload["avg_temperature_c"], float)

    def test_default_date_is_tomorrow(self, service):
        result = service.get_forecast("Moscow")
        expected = date.today() + timedelta(days=1)
        assert result.time == expected

    def test_explicit_date(self, service):
        target = date(2026, 7, 15)
        result = service.get_forecast("Moscow", forecast_date=target)
        assert result.time == target

    def test_model_unavailable_propagates(self, geo_coder, empty_registry):
        svc = ForecastService(geo_coder=geo_coder, model_registry=empty_registry)
        with pytest.raises(ModelNotAvailableError):
            svc.get_forecast("Moscow")

    def test_summer_forecast_warmer_than_winter(self, service):
        jan = service.get_forecast("Saint Petersburg", forecast_date=date(2026, 1, 15))
        jul = service.get_forecast("Saint Petersburg", forecast_date=date(2026, 7, 15))
        assert jul.payload["avg_temperature_c"] > jan.payload["avg_temperature_c"]
