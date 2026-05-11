import pandas as pd
import numpy as np
import pytest
from app.ml.models.xgb_forecaster import XGBForecaster


def test_xgb_fit_predict(tr, ts):
    limit = 7
    X, y = tr.drop(columns=["temperature"]), tr["temperature"]
    model = XGBForecaster()
    model.fit(X, y)
    print("After fit ", X.columns)
    preds = model.predict(
        X_future=ts[:limit],
        X_history=X,
        y_history=y,
    )
    assert len(preds) == limit
    assert isinstance(preds, (np.ndarray, pd.Series, list))
