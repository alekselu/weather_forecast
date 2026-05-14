from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd


class BaseModel(ABC):
    @property
    @abstractmethod
    def version(self) -> str:
        pass

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
    def save(self, path: str) -> None:
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

    def fit(self, df):
        return self

    def predict(self, history, horizon):
        if history.empty:
            return 0.0
        recent_history = history["value"]
        return float(recent_history.mean())

    def update(self, new_data):
        return self

    def save(self, path):
        pass

    @classmethod
    def load(cls, path):
        return cls()
