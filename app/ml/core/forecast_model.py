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
        X_history: pd.Series | None = None,
        y_history: pd.Series | None = None,
    ) -> pd.Series:
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
