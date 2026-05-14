"""
Shared pytest fixtures for all test layers.

Design principles:
- Each test gets a fresh app instance (no shared state between tests).
- The model registry is pre-loaded with ModelStub (no external dependencies).
- GeoService uses offline mode (no real Nominatim calls during tests).
"""

from __future__ import annotations

from datetime import date
import pytest
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from app.main import app, get_geo_coder
from app.ml.model_registry import get_model_registry

from app.ml.model_registry import ModelRegistry, ModelStub
from app.utils.geolocation import GeoCoder
from app.services.forecast_service import ForecastService
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
def model_registry() -> ModelRegistry:
    """Fresh registry with stub model loaded."""
    registry = ModelRegistry()
    registry.load(ModelStub())
    return registry


@pytest.fixture
def empty_registry() -> ModelRegistry:
    """Registry with NO model loaded — simulates cold start / model failure."""
    return ModelRegistry()


@pytest.fixture
def geo_coder() -> GeoCoder:
    """GeoCoder service."""
    return GeoCoder()


@pytest.fixture
def forecast_service(
    geo_coder: GeoCoder, model_registry: ModelRegistry
) -> ForecastService:
    return ForecastService(geo_coder=geo_coder, model_registry=model_registry)


# ── FastAPI test client ──────────────────────────────────────────────────────


@pytest.fixture
def client(model_registry, geo_coder):
    app.dependency_overrides[get_model_registry] = lambda: model_registry
    app.dependency_overrides[get_geo_coder] = lambda: geo_coder
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_no_model(empty_registry, geo_coder):
    app.dependency_overrides[get_model_registry] = lambda: empty_registry
    app.dependency_overrides[get_geo_coder] = lambda: geo_coder
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
