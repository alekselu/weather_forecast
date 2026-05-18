"""
Shared pytest fixtures for all test layers.
"""

from __future__ import annotations

from datetime import date
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
import pandas as pd
import numpy as np
from fastapi.testclient import TestClient
from app.main import app, get_geo_coder
from app.utils.geolocation import GeoCoder
from unittest.mock import AsyncMock, MagicMock
import sys
from pathlib import Path
from asgi_lifespan import LifespanManager

# ── Paths ───────────────────────────────────────────────────────────────────
FIXTURES_DIR = Path(__file__).parent / "fixtures"
CSV_PATH = FIXTURES_DIR / "data_2023_2026.csv"


# ═══════════════════════════════════════════════════════════════════════════
# CSV-данные (реальные, без Postgres)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture(scope="session")
def weather_df() -> pd.DataFrame:
    assert CSV_PATH.exists(), f"CSV test data not found."
    df = pd.read_csv(CSV_PATH, parse_dates=["date"])
    df["city_id"] = 1
    return df.sort_values("date").reset_index(drop=True)


@pytest.fixture(scope="session")
def csv_daily_columns(weather_df: pd.DataFrame) -> list[str]:
    """Columns classified as Open-Meteo daily parameters."""
    from app.params import DAILY_PARAMS

    return [c for c in weather_df.columns if c in DAILY_PARAMS]


@pytest.fixture(scope="session")
def csv_hourly_columns(weather_df: pd.DataFrame) -> list[str]:
    """Columns classified as Open-Meteo hourly parameters."""
    from app.params import HOURLY_PARAMS

    return [c for c in weather_df.columns if c in HOURLY_PARAMS]


# ═══════════════════════════════════════════════════════════════════════════
# Фейки внешних зависимостей
# ═══════════════════════════════════════════════════════════════════════════

# tests/fakes.py

from datetime import timedelta

from app.schemas.forecast import ForecastPayload


class FakeMLClient:
    async def predict(self, request):
        """
        Генерирует фиктивный ForecastPayload
        на основе диапазона дат и списка параметров.
        """

        days = (request.end_date - request.start_date).days + 1

        dates = [
            (request.start_date + timedelta(days=i)).isoformat() for i in range(days)
        ]

        daily = {}
        hourly = {}

        # Daily params
        for param in request.daily:
            if "temperature" in param:
                daily[param] = [10.0 + i for i in range(days)]
            elif "precipitation" in param:
                daily[param] = [0.1 * i for i in range(days)]
            else:
                daily[param] = [float(i) for i in range(days)]

        # Hourly params
        total_hours = days * 24

        for param in request.hourly:
            if "temperature" in param:
                hourly[param] = [15.0 + (i % 24) * 0.1 for i in range(total_hours)]
            else:
                hourly[param] = [float(i) for i in range(total_hours)]

        # Обычно Open-Meteo payload содержит time
        if daily:
            daily["time"] = dates

        if hourly:
            hourly["time"] = [
                f"{date}T{hour:02d}:00" for date in dates for hour in range(24)
            ]

        return ForecastPayload(
            hourly=hourly,
            daily=daily,
        )

    async def health(self):
        return {"status": "ok"}

    async def aclose(self):
        pass


class FakeGeoCoder:
    """
    Does not make HTTP-requests.
    city.name == 'unknown'  -> LookupError  (тест 404)
    other                   -> Coordinates of St Petersburg (as in CSV)
    """

    async def fetch_location_from(self, city):
        from app.utils.structures import Coordinates

        if city.name.lower() == "unknown":
            raise LookupError(f"City not found: {city.name}")
        return Coordinates(latitude=59.57, longitude=30.19)


class FakeAsyncSession:
    """
    AsyncSession stub (SQLAlchemy).
    Tests using real DB rows patch execute() themselves.
    """

    async def execute(self, *args, **kwargs):
        result = MagicMock()
        result.fetchall.return_value = []
        result.scalars.return_value.all.return_value = []
        return result

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        pass


@pytest.fixture
def fake_geocoder() -> FakeGeoCoder:
    return FakeGeoCoder()


@pytest.fixture
def fake_db_session() -> FakeAsyncSession:
    return FakeAsyncSession()


@pytest.fixture
def fake_ml_client() -> FakeMLClient:
    return FakeMLClient()


# ═══════════════════════════════════════════════════════════════════════════
# ModelRegistry-заглушки (три состояния)
# ═══════════════════════════════════════════════════════════════════════════


class _BaseRegistry:
    version: str = "test-v1"
    retraining: bool = False

    def is_ready(self) -> bool:
        raise NotImplementedError

    @property
    def active(self):
        raise NotImplementedError


class FakeRegistryReady(_BaseRegistry):
    def is_ready(self) -> bool:
        return True

    @property
    def active(self):
        return MagicMock()


class FakeRegistryNotReady(_BaseRegistry):
    version = "none"

    def is_ready(self) -> bool:
        return False

    @property
    def active(self):
        return None


class FakeRegistryRetraining(_BaseRegistry):
    retraining = True

    def is_ready(self) -> bool:
        return True

    @property
    def active(self):
        return MagicMock()


@pytest.fixture(scope="session")
def fake_registry_ready():
    return FakeRegistryReady()


@pytest.fixture(scope="session")
def fake_registry_not_ready():
    return FakeRegistryNotReady()


@pytest.fixture(scope="session")
def fake_registry_retraining():
    return FakeRegistryRetraining()


# ═══════════════════════════════════════════════════════════════════════════
# HTTP-clients (ASGI — no real network)
# ═══════════════════════════════════════════════════════════════════════════


@pytest_asyncio.fixture
async def client(fake_geocoder, fake_registry_ready):
    """Client: GeoCoder and Registry work as intended."""
    from app.main import app as _app, predictor
    from app.dependencies import get_geo_coder, get_model_registry, get_ml_client

    _app.dependency_overrides[get_geo_coder] = lambda: fake_geocoder
    _app.dependency_overrides[get_model_registry] = lambda: fake_registry_ready
    # app.dependency_overrides[get_ml_client] = lambda: fake_ml_client

    async with LifespanManager(_app):
        async with AsyncClient(
            transport=ASGITransport(app=_app),
            base_url="http://localhost:8000",
        ) as ac:
            yield ac
    # async with AsyncClient(
    #     transport=ASGITransport(app=_app), base_url="http://localhost:8000"
    # ) as ac:
    #     yield ac

    _app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_no_model(fake_geocoder, fake_registry_not_ready):
    """Client: model not loaded -> expecting 503."""
    from app.main import app
    from app.dependencies import get_geo_coder, get_model_registry

    app.dependency_overrides[get_geo_coder] = lambda: fake_geocoder
    app.dependency_overrides[get_model_registry] = lambda: fake_registry_not_ready

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_retraining(fake_geocoder, fake_registry_retraining):
    """Client: retraining in process."""
    from app.main import app
    from app.dependencies import get_geo_coder, get_model_registry

    app.dependency_overrides[get_geo_coder] = lambda: fake_geocoder
    app.dependency_overrides[get_model_registry] = lambda: fake_registry_retraining

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def valid_daily_params() -> list[str]:
    return ["temperature_2m_mean", "temperature_2m_max"]


@pytest.fixture
def valid_hourly_params() -> list[str]:
    return ["temperature_2m", "precipitation"]


# ═══════════════════════════════════════════════════════════════════════════
# Older test fixtures
# ═══════════════════════════════════════════════════════════════════════════
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
        },
        errors="ignore",
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
def plain_client():
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
