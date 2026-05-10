import pandas as pd
import numpy as np
import pytest
from app.ml.models.xgb_forecaster import XGBForecaster


def test_xgb_fit_predict(training_data, future_data):
    # Инициализация
    model = XGBForecaster(target_column="temperature")

    # Обучение
    model.fit(training_data)

    # Предсказание
    preds = model.predict(
        X_history=training_data,
        future_covariates=future_data,
    )

    # Проверки
    assert len(preds) == 7
    assert isinstance(preds, (np.ndarray, pd.Series, list))
