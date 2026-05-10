import joblib
import pandas as pd
from statsmodels.tsa.statespace.sarimax import (
    SARIMAX,
)

from app.ml.preprocessing.sarimax_preprocessor import (
    SARIMAXPreprocessor,
)
from app.ml.core.forecast_model import ForecastModel


class SARIMAXForecaster(ForecastModel):
    def __init__(
        self,
        order=(1, 1, 1),
        seasonal_order=(1, 1, 1),
    ):
        self.order = order
        self.seasonal_order = seasonal_order
        self.preprocessor = SARIMAXPreprocessor()
        self.model = None
        self.results = None

    def fit(self, X, y):
        df = self.preprocessor.transform(X, y)
        X = df[
            [
                "day_sin",
                "day_cos",
                "weekday_sin",
                "weekday_cos",
                "month_sin",
                "month_cos",
            ]
        ]
        self.model = SARIMAX(
            endog=y,
            exog=X,
            order=self.order,
            seasonal_order=self.seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        self.results = self.model.fit(disp=False)
        return self

    def predict(self, X_future, X_history=None, y_history=None):
        X_future = self.preprocessor.transform(X_future)
        X_future = X_future[
            [
                "day_sin",
                "day_cos",
                "weekday_sin",
                "weekday_cos",
                "month_sin",
                "month_cos",
            ]
        ]
        forecast = self.results.forecast(
            steps=len(X_future),
            exog=X_future,
        )
        return pd.Series(forecast.tolist())

    def save(self, path):
        joblib.dump(
            {
                "results": self.results,
                "order": self.order,
                "seasonal_order": self.seasonal_order,
            }
        )
        self.results.save(path)

    @classmethod
    def load(cls, path):
        data = joblib.load(path)
        obj = cls(order=data["order"], seasonal_order=data["seasonal_order"])
        obj.results = data["results"]
        return obj
