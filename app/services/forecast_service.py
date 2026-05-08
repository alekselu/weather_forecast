"""
ForecastService: orchestrates geo resolution → feature building → model prediction.

This is the central business-logic component that the API layer calls.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.core.exceptions import ModelNotAvailableError
from app.ml.model_registry import FeatureVector, ModelRegistry
from app.schemas.forecast import ForecastResponse
from app.services.geo_service import GeoService
import logging


logger = logging.getLogger(__name__)


class ForecastService:
    def __init__(self, geo_service: GeoService, model_registry: ModelRegistry) -> None:
        self._geo = geo_service
        self._registry = model_registry

    def get_forecast(
        self, city: str, forecast_date: date | None = None
    ) -> ForecastResponse:
        """
        Return a temperature forecast for the given city and date.

        Args:
            city: Human-readable city name.
            forecast_date: Target date. Defaults to tomorrow (server time).

        Returns:
            ForecastResponse with predicted avg temperature.

        Raises:
            CityNotFoundError: If the city cannot be geocoded.
            ModelNotAvailableError: If no model is loaded.
            InsufficientDataError: If historical data is missing (v1+).
        """
        target_date = forecast_date or (date.today() + timedelta(days=1))

        logger.info("forecast_requested", city=city, target_date=str(target_date))

        # 1. Resolve city → coordinates
        location = self._geo.resolve(city)

        # 2. Build feature vector
        #    v0: only lat/lon + date are populated; lags filled by DB in v1+
        doy = target_date.timetuple().tm_yday
        features = FeatureVector(
            city=location.city,
            forecast_date=target_date,
            lat=location.latitude,
            lon=location.longitude,
            day_of_year=doy,
            month=target_date.month,
            day_of_week=target_date.weekday(),
        )

        # 3. Run prediction
        if not self._registry.is_ready:
            raise ModelNotAvailableError("No model loaded in registry")

        predicted_temp = self._registry.predict(features)

        logger.info(
            "forecast_produced",
            city=location.city,
            date=str(target_date),
            temp=predicted_temp,
            model=self._registry.current_version,
        )

        return ForecastResponse(
            city=location.city,
            date=target_date,
            avg_temperature_c=predicted_temp,
            model_version=self._registry.current_version,
        )
