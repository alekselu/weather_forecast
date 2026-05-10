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
        horizon: int,
    ):
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
