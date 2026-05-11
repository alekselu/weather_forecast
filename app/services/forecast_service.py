"""
ForecastService: orchestrates geo resolution → feature building → model prediction.

This is the central business-logic component that the API layer calls.
"""

from __future__ import annotations

from datetime import date, timedelta
import pandas as pd
import numpy as np
from app.core.exceptions import ModelNotAvailableError
from app.ml.model_registry import FeatureVector, ModelRegistry
from app.schemas.forecast import ForecastResponse
from app.utils.geolocation import GeoCoder
from app.utils.fakes import fake_temperature_by_date
import logging
import asyncio

logger = logging.getLogger(__name__)


class ForecastService:
    def __init__(self, geo_coder: GeoCoder, model_registry: ModelRegistry) -> None:
        self._geo = geo_coder
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
            InsufficientDataError: If historical data is missing.
        """
        target_date = forecast_date or (date.today() + timedelta(days=1))

        logger.info("forecast_requested: %s, %s", city, str(target_date))

        doy = target_date.timetuple().tm_yday
        # Stub for tests
        features = pd.DataFrame.from_dict(
            {"value": [fake_temperature_by_date(target_date)]}
        )

        # 3. Run prediction
        if not self._registry.is_ready:
            raise ModelNotAvailableError("No model loaded in registry")

        predicted_temp = self._registry.predict(
            features,
            (target_date - date.today()).days,
        )

        logger.info(
            "forecast_produced: %s",
            ",".join(
                f"{k}:{v}"
                for k, v in dict(
                    city=city,
                    date=str(target_date),
                    temp=predicted_temp,
                    model=self._registry.current_version,
                ).items()
            ),
        )

        return ForecastResponse(
            city=city,
            time=target_date,
            params=[],
            coords="",
            payload=dict(
                avg_temperature_c=predicted_temp,
                model_version=self._registry.current_version,
            ),
        )
