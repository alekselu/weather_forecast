"""
Shared pytest fixtures for all test layers.
"""

from __future__ import annotations

from datetime import date
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from app.main import app, get_geo_coder
from app.utils.geolocation import GeoCoder
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


@pytest.fixture(scope="session")
def raw_weather_df():
    path = Path(__file__).parent.parent / "experiments" / "data_2023_2026.csv"
    df = pd.read_csv(path, parse_dates=["time"], date_format="%Y-%m-%d")
    df = df.rename(
        columns={
            "time": "date",
            "temperature_2m_mean (°C)": "temperature",
        }
    )
    df["city_id"] = 1
    return df


@pytest.fixture(scope="session")
def target_column():
    return "temperature"


@pytest.fixture(scope="session")
def weather_df(
    raw_weather_df,
    target_column,
):
    df = raw_weather_df.copy()
    df = df.sort_values("date")
    return df


@pytest.fixture(scope="session")
def X(weather_df, target_column):
    return weather_df.drop(
        columns=[
            target_column,
        ]
    )


@pytest.fixture(scope="session")
def y(weather_df, target_column):
    return weather_df[target_column]


# ── Isolated service fixtures ────────────────────────────────────────────────


@pytest.fixture
def geo_coder() -> GeoCoder:
    """GeoCoder service."""
    return GeoCoder()


# ── FastAPI test client ──────────────────────────────────────────────────────


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helpers ──────────────────────────────────────────────────────────────────

TOMORROW = str(
    date.today().replace(day=date.today().day + 1)
    if date.today().day < 28
    else (
        date.today().replace(month=date.today().month + 1, day=1)
        if date.today().month < 12
        else date.today().replace(year=date.today().year + 1, month=1, day=1)
    )
)

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
