import pandas as pd
import numpy as np
import pytest
from app.ml.models.sarimax_forecaster import SARIMAXForecaster


def test_sarimax_fit_predict(training_data, future_data):
    model = SARIMAXForecaster()
    model.fit(training_data)
    preds = model.predict(future_data)
    assert len(preds) == 7
