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
from fastapi.testclient import TestClient
from app.main import app, get_geo_coder
from app.ml.model_registry import get_model_registry

from app.ml.model_registry import ModelRegistry, ModelStub
from app.utils.geolocation import GeoCoder
from app.services.forecast_service import ForecastService
import sys
from pathlib import Path

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
