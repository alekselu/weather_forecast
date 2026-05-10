import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path


@pytest.fixture
def common_train_df():
    dates = pd.date_range("2020-01-01", periods=400)
    return pd.DataFrame(
        {
            "date": dates,
            "temperature": np.sin(np.arange(400) / 30),
        }
    )


@pytest.fixture
def common_future_df():
    return pd.DataFrame({"date": pd.date_range("2021-02-05", periods=7)})


sys.path.insert(0, str(Path(__file__).parent.parent.parent))
