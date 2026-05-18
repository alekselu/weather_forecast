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
        seasonal_order=None,
    ):
        self.order = order
        self.seasonal_order = seasonal_order
        self.preprocessor = SARIMAXPreprocessor()
        self.model = None
        self.results = None
        self.exog_cols = [
            "day_of_year_sin",
            "day_of_year_cos",
            "weekday_sin",
            "weekday_cos",
            "month_sin",
            "month_cos",
        ]

    def _prepare(self, X: pd.DataFrame, y: pd.Series | None = None):
        df, y_out = self.preprocessor.transform(X, y)
        X_out = df[self.exog_cols].copy()
        return X_out, y_out

    def fit(self, X, y):
        X, y = self._prepare(X, y)
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
        X_future, _ = self._prepare(X_future)
        forecast = self.results.forecast(
            steps=len(X_future),
            exog=X_future,
        )
        return pd.Series(forecast.tolist())

    def update(self, X_new, y_new, refit=False):
        X_new, y_new = self._prepare(X_new, y_new)
        self.results = self.results.append(endog=y_new, exog=X_new, refit=refit)
        return self

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
