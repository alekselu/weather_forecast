from abc import ABC, abstractmethod
import pandas as pd


class ForecastModel(ABC):
    @abstractmethod
    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
    ):
        pass

    @abstractmethod
    def predict(
        self,
        X_future: pd.DataFrame,
        X_history: pd.Series,
        y_history: pd.Series,
    ) -> pd.Series:
        pass

    @abstractmethod
    def update(
        self,
        X_new: pd.DataFrame,
        y_new: pd.Series,
        refit: bool = False,
    ):
        pass

    @abstractmethod
    def save(
        self,
        path: str,
    ):
        pass

    @classmethod
    @abstractmethod
    def load(
        cls,
        path: str,
    ):
        pass


class ModelStub(ForecastModel):
    """
    Stub model — returns a naive seasonal estimate based on latitude and
    day-of-year sinusoidal approximation.

    Saint Petersburg (lat≈60°N):
        Jan mean ≈ -5°C, Jul mean ≈ +18°C  → amplitude ≈ 11.5, centre ≈ 6.5
    Generic formula: T = base + amplitude * sin((doy - 80) * 2π / 365)
    where base and amplitude are derived from latitude.

    This is intentionally simple and clearly labelled as a stub.
    """

    def fit(self, X, y):
        return self

    def predict(self, X_future, X_history, y_history):
        if X_history.empty:
            return 0.0
        recent_history = X_history["value"]
        return float(recent_history.mean())

    def save(self, path):
        pass

    @classmethod
    def load(cls, path):
        return cls()
