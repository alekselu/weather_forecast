import joblib
import pandas as pd
import numpy as np

from xgboost import XGBRegressor

from app.ml.preprocessing.xgb_preprocessor import (
    XGBPreprocessor,
)
from app.ml.core.forecast_model import ForecastModel


class XGBForecaster(ForecastModel):
    def __init__(
        self,
        params=None,
        model=None,
    ):
        self.preprocessor = XGBPreprocessor()
        self.params = params or {}
        self.model = XGBRegressor(**self.params) if model is None else model

    def fit(self, X, y):
        df = self.preprocessor.transform(X, y)
        X = df.drop(
            columns=[
                "date",
                self.target_column,
            ]
        )
        self.model.fit(X, y)
        return self

    def predict(self, X_future, X_history=None, y_history=None):
        X_history = X_history.copy()
        predictions = pd.Series([])
        for i in range(len(X_future)):
            combined = pd.concat(
                [
                    X_history,
                    X_future.iloc[: i + 1],
                ]
            )
            processed = self.preprocessor.transform(
                combined, pd.concat([y_history, np.nan])
            )

            latest = processed.iloc[-1:]
            X = latest.drop(
                columns=[
                    "date",
                ]
            )
            pred = self.model.predict(X)[0]
            predictions = pd.concat([predictions, pred])
            next_row = X_future.iloc[i : i + 1].copy()
            # next_row[self.target_column] = pred
            X_history = pd.concat([X_history, next_row])
        return predictions

    def save(self, path):
        joblib.dump(
            {
                "model": self.model,
                "params": self.params,
            },
            path,
        )

    @classmethod
    def load(cls, path):
        data = joblib.load(path)
        obj = cls(
            params=data["params"],
        )
        obj.model = data["model"]
        return obj
