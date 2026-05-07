from app.ml.xgb_model import XGBWeatherModel
from app.ml.sarimax_model import SARIMAXModel
from app.ml.tuning import evaluate_model


class ModelSelector:
    def __init__(self):
        self.model = None

    def train(self, X, y):
        # 1. обучаем XGBoost
        # xgb = XGBWeatherModel()
        # xgb_score = evaluate_model(xgb, X, y)

        # # 2. обучаем SARIMAX
        # sarimax = SARIMAXModel()
        # sarimax_score = evaluate_model(sarimax, X, y)

        # # 3. сравнение
        # if sarimax_score < xgb_score:
        #     self.model = sarimax
        # else:
        #     self.model = xgb
        self.model = SARIMAXModel()

        # финальное обучение
        self.model.fit(X, y)

    def predict(self, X):
        return self.model.predict(X)

    def update(self, X, y):
        self.model.update(X, y)
