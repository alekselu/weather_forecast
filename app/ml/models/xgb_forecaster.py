import joblib
import pandas as pd
import numpy as np

from xgboost import XGBRegressor

from app.ml.preprocessing.xgb_preprocessor import XGBPreprocessor
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
        X, y = self.preprocessor.transform(X, y)
        X = X.drop(
            columns=[
                "date",
            ],
            errors="ignore",
        )
        print(f"In fit: {len(X)}, {len(y)}")
        self.model.fit(X, y)
        return self

    def predict(self, X_future, X_history, y_history):
        X_history = X_history.copy()
        predictions = pd.Series([])
        for i in range(len(X_future)):
            combined = pd.concat(
                [
                    X_history,
                    X_future.iloc[i : i + 1],
                ],
                ignore_index=True,
            )
            X_processed, y_processed = self.preprocessor.transform(
                combined, pd.concat([y_history, y_history[-1:]], ignore_index=True)
            )

            latest = X_processed.iloc[-1:]
            X = latest.drop(
                columns=[
                    "date",
                ],
                errors="ignore",
            )
            pred = pd.Series([self.model.predict(X)[0]])
            predictions = pd.concat([predictions, pred], ignore_index=True)
            next_row = X_future.iloc[i : i + 1].copy()
            X_history = pd.concat([X_history, next_row], ignore_index=True)
            y_history = pd.concat([y_history, pred], ignore_index=True)
            print("After pred: ", len(X_history), len(y_history))
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
