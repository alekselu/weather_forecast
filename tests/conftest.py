import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path


@pytest.fixture
def train_df():
    """Basic fixture for training data"""
    count = 40
    dates = pd.date_range("2020-01-01", periods=count, freq="D")
    return pd.DataFrame(
        {
            "date": dates,
            "city_id": 1,
            "temperature": np.sin(np.arange(count) / 10),
            "humidity": np.cos(np.arange(count) / 10),
        }
    )


@pytest.fixture
def test_df(train_df):
    """Basic fixture for future dates"""
    count = 7
    last_date = train_df["date"].max()
    dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=count, freq="D")
    return pd.DataFrame({"date": dates, "city_id": 1})


@pytest.fixture
def tr(train_df):
    return train_df


@pytest.fixture
def ts(test_df):
    return test_df


sys.path.insert(0, str(Path(__file__).parent.parent.parent))
