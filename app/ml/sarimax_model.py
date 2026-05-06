import pandas as pd
from darts import TimeSeries
from darts.models import SARIMAX
from app.ml.base_model import BaseModel


class SARIMAXModel(BaseModel):
    def __init__(self, order=(1, 1, 1), seasonal_order=(1, 1, 1, 365)):
        self.order = order
        self.seasonal_order = seasonal_order
        self.models = {}

    def fit(self, X, y):
        for col in y.columns:
            series = TimeSeries.from_series(y[col])
            model = SARIMAX(order=self.order, seasonal_order=self.seasonal_order)
            model.fit(series)
            self.models[col] = model

    def predict(self, X):
        result = {}
        for col, model in self.models.items():
            forecast = model.predict(1)
            result[col] = forecast.values().flatten()[0]
        return pd.DataFrame([result])

    def update(self, X, y):
        self.fit(X, y)

    def save(self, path):
        pass

    def load(self, path):
        pass
