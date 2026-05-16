from collections import defaultdict
import pandas as pd
import joblib, os
from app.ml.core.forecast_model import ForecastModel


class ForecasterEnsemble:
    def __init__(self):
        self.models = defaultdict(dict)
        self.is_global = {}

    def register_model(self, target: str, model: ForecastModel, city: str = None):
        if city is None:
            self.models[target]["global"] = model
            self.is_global[target] = True
        else:
            self.models[target][city] = model
            self.is_global[target] = False

    def predict(
        self,
        city: str,
        target: str,
        X_future: pd.DataFrame,
        X_history: pd.DataFrame,
        y_history: pd.Series,
    ):
        if self.is_global.get(target):
            model = self.models[target]["global"]
        else:
            model = self.models[target].get(city)
        if model is None:
            raise ValueError(f"No model found for {target} in {city}")

        return model.predict(X_future, X_history, y_history)

    def save(self, path: str) -> None:
        os.makedirs(path, exist_ok=True)
        joblib.dump(self, os.path.join(path, "ensemble.pkl"))

    @classmethod
    def load(cls, path: str) -> "ForecasterEnsemble":
        return joblib.load(os.path.join(path, "ensemble.pkl"))
