import pandas as pd
import numpy as np
import pytest
from app.ml.models.xgb_forecaster import XGBForecaster


def test_xgb_fit_predict(training_data, future_data):
    limit = 7
    X, y = training_data.drop(columns=["temperature"]), training_data["temperature"]
    model = XGBForecaster()
    model.fit(X, y)
    print("After fit ", X.columns)
    preds = model.predict(
        X_future=future_data[:limit],
        X_history=X,
        y_history=y,
    )
    assert len(preds) == limit
    assert isinstance(preds, (np.ndarray, pd.Series, list))
