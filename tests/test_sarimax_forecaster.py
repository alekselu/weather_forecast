import pandas as pd
import numpy as np
import pytest
from app.ml.models.sarimax_forecaster import SARIMAXForecaster


def test_sarimax_fit_predict(sample_data, future_dates):
    model = SARIMAXForecaster(target_column="temperature")

    model.fit(sample_data)

    # Согласно вашему коду, здесь передается только future
    preds = model.predict(future_dates)

    assert len(preds) == 7
