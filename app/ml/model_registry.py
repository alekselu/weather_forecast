"""
ML layer: abstract interface + stub implementation.

The stub returns a deterministic seasonal estimate so the API
is fully functional before the real XGBoost/LightGBM model is ready.
Replace ModelStub with a real ModelAdapter when the model artifact exists.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional
import logging
from app.core.exceptions import ModelNotAvailableError

logger = logging.getLogger(__name__)


@dataclass
class FeatureVector:
    """Input features for temperature prediction."""

    city: str
    forecast_date: date
    lat: float
    lon: float
    # Populated after DB query (may be None for stub)
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
    @abstractmethod
    def fit(self, df: pd.DataFrame):
        pass

    @abstractmethod
    def predict(self, history: pd.DataFrame, horizon: int):
        pass

    @abstractmethod
    def update(self, new_data: pd.DataFrame):
        pass

    @abstractmethod
    def save(self, path: str):
        pass

    @classmethod
    @abstractmethod
    def load(cls, path: str):
        pass


class ModelStub(BaseModel):
    """
    Stub model — returns a naive seasonal estimate based on latitude and
    day-of-year sinusoidal approximation.

    Saint Petersburg (lat≈60°N):
        Jan mean ≈ -5°C, Jul mean ≈ +18°C  → amplitude ≈ 11.5, centre ≈ 6.5
    Generic formula: T = base + amplitude * sin((doy - 80) * 2π / 365)
    where base and amplitude are derived from latitude.

    This is intentionally simple and clearly labelled as a stub.
    """

    VERSION = "stub-v0"

    @property
    def version(self) -> str:
        return self.VERSION

    @property
    def is_ready(self) -> bool:
        return True  # stub is always ready

    def predict(self, features: FeatureVector) -> float:
        doy = features.day_of_year or features.forecast_date.timetuple().tm_yday
        lat = features.lat

        # Rough latitude-based seasonal parameters
        # At equator: base=25, amplitude=5; at 60°N: base=6, amplitude=14
        t = max(0.0, min(1.0, (lat - 0) / 90))  # 0..1 pole fraction
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
    Usage:
        registry = ModelRegistry()
        registry.load(ModelStub())   # on startup
        prediction = registry.predict(features)
        registry.swap(new_model)     # during retraining
    """

    def __init__(self) -> None:
        self._model: Optional[BaseModel] = None

    def load(self, model: BaseModel) -> None:
        """Load initial model (call on startup)."""
        self._model = model
        logger.info("model_loaded", version=model.version)

    def swap(self, new_model: BaseModel) -> None:
        """Atomically replace the current model (hot-swap during retraining)."""
        old_version = self._model.version if self._model else "none"
        self._model = new_model
        logger.info("model_swapped", old=old_version, new=new_model.version)

    @property
    def is_ready(self) -> bool:
        return self._model is not None and self._model.is_ready

    @property
    def current_version(self) -> str:
        return self._model.version if self._model else "none"

    def predict(self, history: pd.DataFrame, horizon: int) -> float:
        if not self.is_ready:
            raise ModelNotAvailableError("Registry has no loaded model")
        return self._model.predict(features)


_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    return _registry
