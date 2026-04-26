"""
ForecastService: orchestrates geo resolution → feature building → model prediction.

Это центральный компонент бизнес-логики, который вызывает API слой.
"""

from __future__ import annotations

from datetime import date, timedelta

from app.core.exceptions import ModelNotAvailableError
from app.core.logging import get_logger
from app.ml.model_registry import FeatureVector, ModelRegistry
from app.schemas.forecast import ForecastResponse
from app.services.geo_service import GeoService

logger = get_logger(__name__)


class ForecastService:
    """Сервис прогнозирования: геокодирование → построение признаков → предсказание модели."""

    def __init__(self, geo_service: GeoService, model_registry: ModelRegistry) -> None:
        self._geo = geo_service
        self._registry = model_registry

    def get_forecast(self, city: str, forecast_date: date | None = None) -> ForecastResponse:
        """
        Возвращает прогноз температуры для указанного города и даты.

        Args:
            city: Человекочитаемое название города.
            forecast_date: Целевая дата. По умолчанию — завтрашний день (время сервера).

        Returns:
            ForecastResponse с прогнозируемой средней температурой.

        Raises:
            CityNotFoundError: Если город не удаётся геокодировать.
            ModelNotAvailableError: Если не загружена ни одна модель.
            InsufficientDataError: Если отсутствуют исторические данные (v1+).
        """
        target_date = forecast_date or (date.today() + timedelta(days=1))

        logger.info("forecast_requested", city=city, target_date=str(target_date))

        # 1. Преобразуем город в координаты
        location = self._geo.resolve(city)

        # 2. Строим вектор признаков
        #    v0: заполнены только широта/долгота + дата; лаги заполняются из БД в v1+
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

        # 3. Выполняем предсказание
        if not self._registry.is_ready:
            raise ModelNotAvailableError("В реестре нет загруженной модели")

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
