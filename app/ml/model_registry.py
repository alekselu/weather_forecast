"""
ML слой: абстрактный интерфейс + заглушка (stub).

Заглушка возвращает детерминированную сезонную оценку, чтобы API
был полностью работоспособен до того, как будет готова реальная модель XGBoost/LightGBM.
Замените ModelStub на реальный ModelAdapter, когда появится артефакт модели.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class FeatureVector:
    """Входные признаки для предсказания температуры."""
    city: str
    forecast_date: date
    lat: float
    lon: float
    # Заполняется после запроса к БД (может быть None для заглушки)
    lag_1: Optional[float] = None
    lag_2: Optional[float] = None
    lag_3: Optional[float] = None
    lag_7: Optional[float] = None
    lag_14: Optional[float] = None
    lag_30: Optional[float] = None
    rolling_mean_7d: Optional[float] = None
    day_of_year: Optional[int] = None
    month: Optional[int] = None
    day_of_week: Optional[int] = None


class BaseModel(ABC):
    """Абстрактная база для всех моделей прогнозирования."""

    @property
    @abstractmethod
    def version(self) -> str: ...

    @property
    @abstractmethod
    def is_ready(self) -> bool: ...

    @abstractmethod
    def predict(self, features: FeatureVector) -> float:
        """Возвращает прогнозируемую среднюю температуру в °C."""
        ...


class ModelStub(BaseModel):
    """
    Модель-заглушка — возвращает наивную сезонную оценку, основанную на широте
    и синусоидальной аппроксимации дня в году.

    Санкт-Петербург (широта ≈ 60° с.ш.):
        Средняя температура в январе ≈ -5°C, в июле ≈ +18°C → амплитуда ≈ 11.5, центр ≈ 6.5
    Общая формула: T = base + amplitude * sin((doy - 80) * 2π / 365)
    где base и amplitude выводятся из широты.

    Это намеренно просто и явно помечено как заглушка.
    """

    VERSION = "stub-v0"

    @property
    def version(self) -> str:
        return self.VERSION

    @property
    def is_ready(self) -> bool:
        return True  # заглушка всегда готова

    def predict(self, features: FeatureVector) -> float:
        doy = features.day_of_year or features.forecast_date.timetuple().tm_yday
        lat = features.lat

        # Грубые сезонные параметры на основе широты
        # На экваторе: base=25, amplitude=5; на 60° с.ш.: base=6, amplitude=14
        t = max(0.0, min(1.0, (lat - 0) / 90))  # 0..1 доля широты от экватора к полюсу
        base = 25.0 - 19.0 * t
        amplitude = 5.0 + 9.0 * t

        temp = base + amplitude * math.sin((doy - 80) * 2 * math.pi / 365)
        result = round(temp, 1)

        logger.info(
            "stub_prediction",
            city=features.city,
            date=str(features.forecast_date),
            lat=lat,
            doy=doy,
            predicted=result,
        )
        return result


class ModelRegistry:
    """
    Потокобезопасный реестр моделей с поддержкой атомарной горячей замены (hot-swap).

    Использование:
        registry = ModelRegistry()
        registry.load(ModelStub())   # при запуске
        prediction = registry.predict(features)
        registry.swap(new_model)     # во время дообучения
    """

    def __init__(self) -> None:
        self._model: Optional[BaseModel] = None

    def load(self, model: BaseModel) -> None:
        """Загрузить начальную модель (вызывать при запуске)."""
        self._model = model
        logger.info("model_loaded", version=model.version)

    def swap(self, new_model: BaseModel) -> None:
        """Атомарно заменить текущую модель (горячая замена во время дообучения)."""
        old_version = self._model.version if self._model else "none"
        self._model = new_model
        logger.info("model_swapped", old=old_version, new=new_model.version)

    @property
    def is_ready(self) -> bool:
        return self._model is not None and self._model.is_ready

    @property
    def current_version(self) -> str:
        return self._model.version if self._model else "none"

    def predict(self, features: FeatureVector) -> float:
        from app.core.exceptions import ModelNotAvailableError
        if not self.is_ready:
            raise ModelNotAvailableError("В реестре нет загруженной модели")
        return self._model.predict(features)  # type: ignore[union-attr]


# Синглтон реестра — внедряется через зависимость FastAPI
_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    """Возвращает глобальный реестр моделей (синглтон)."""
    return _registry