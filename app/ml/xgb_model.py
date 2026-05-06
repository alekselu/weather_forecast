import pandas as pd
from xgboost import XGBRegressor
from sklearn.multioutput import MultiOutputRegressor
import joblib
from app.ml.base_model import BaseModel


class XGBWeatherModel(BaseModel):
    def __init__(self, params=None):
        self.params = params or {
            "n_estimators": 300,
            "max_depth": 5,
            "learning_rate": 0.05,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
        }
        self.model = MultiOutputRegressor(XGBRegressor(**self.params))

    def fit(self, X, y):
        self.model.fit(X, y)
        return self

    def predict(self, X):
        return self.model.predict(X)

    def update(self, X, y):
        self.model.fit(X, y)
        return self

    def save(self, path):
        joblib.dump(self.model, path)

    def load(self, path):
        self.model = joblib.load(path)
