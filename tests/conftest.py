import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path


@pytest.fixture
def training_data():
    count = 40
    dates = pd.date_range("2020-01-01", periods=count, freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "temperature": np.sin(
                np.arange(count) / 10
            ),  # Уменьшил делитель, чтобы синусоида была видна на 40 точках
        }
    )


@pytest.fixture
def future_data(training_data):
    count = 40
    last_date = training_data["date"].max()
    start_date = last_date + pd.Timedelta(days=1)

    dates = pd.date_range(start_date, periods=count, freq="D")
    return pd.DataFrame({"date": dates})


sys.path.insert(0, str(Path(__file__).parent.parent.parent))
