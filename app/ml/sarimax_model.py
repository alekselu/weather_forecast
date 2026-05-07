import pandas as pd
import statsmodels.api as sm
from app.ml.base_model import BaseModel


class SARIMAXModel(BaseModel):
    def __init__(self, order=(1, 1, 1), seasonal_order=(1, 1, 1, 365)):
        self.order = order
        self.seasonal_order = seasonal_order
        self.model = None

    def fit(self, X, y):
        self.model = sm.tsa.statespace.SARIMAX(
            y,
            exog=X,
            order=(2, 1, 2),
            # seasonal_order=(1, 1, 1, 365)
        )
        self.res = self.model.fit(disp=False)
        return self

    def predict(self, X):
        return self.res.forecast(
            len(X),
            exog=X,
        )

    def update(self, X, y):
        self.fit(X, y)
        return self

    def save(self, path):
        pass

    def load(self, path):
        pass
