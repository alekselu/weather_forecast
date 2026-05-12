"""
ML layer: abstract interface + stub implementation.

The stub returns a deterministic seasonal estimate so the API
is fully functional before the real XGBoost/LightGBM model is ready.
Replace ModelStub with a real ModelAdapter when the model artifact exists.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Optional
import logging
from app.ml.core.base_model import BaseModel, ModelStub
import pandas as pd

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
        logger.info(f"model_loaded, version = {model.version}")

    def swap(self, new_model: BaseModel) -> None:
        """Atomically replace the current model (hot-swap during retraining)."""
        old_version = self._model.version if self._model else "none"
        self._model = new_model
        logger.info(f"model_swapped, old={old_version}, new={new_model.version}")

    @property
    def is_ready(self) -> bool:
        return self._model is not None and self._model.is_ready

    @property
    def current_version(self) -> str:
        return self._model.version if self._model else "none"

    def predict(self, history: pd.DataFrame, horizon: int) -> float:
        if not self.is_ready:
            raise Exception("Registry has no loaded model")
        return self._model.predict(history, horizon)


_registry = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    return _registry
