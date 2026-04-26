"""
Общие pytest фикстуры для всех слоёв тестирования.

Принципы проектирования:
- Каждый тест получает свежий экземпляр приложения (нет общего состояния между тестами).
- Реестр моделей предварительно загружен с ModelStub (нет внешних зависимостей).
- GeoService использует офлайн-режим (без реальных вызовов Nominatim во время тестов).
"""

from __future__ import annotations

from datetime import date
import pytest
from fastapi.testclient import TestClient

from app.ml.model_registry import ModelRegistry, ModelStub
from app.services.geo_service import GeoService
from app.services.forecast_service import ForecastService


# ── Изолированные фикстуры сервисов ────────────────────────────────────────────────

@pytest.fixture
def model_registry() -> ModelRegistry:
    """Свежий реестр с загруженной моделью-заглушкой."""
    registry = ModelRegistry()
    registry.load(ModelStub())
    return registry


@pytest.fixture
def empty_registry() -> ModelRegistry:
    """Реестр БЕЗ загруженной модели — симулирует холодный старт / отказ модели."""
    return ModelRegistry()


@pytest.fixture
def geo_service() -> GeoService:
    """GeoService с отключённым геокодером — использует только встроенный список известных городов."""
    return GeoService(use_geocoder=False)


@pytest.fixture
def forecast_service(geo_service: GeoService, model_registry: ModelRegistry) -> ForecastService:
    """Сервис прогнозирования с внедрёнными зависимостями."""
    return ForecastService(geo_service=geo_service, model_registry=model_registry)


# ── Тестовый клиент FastAPI ──────────────────────────────────────────────────────

@pytest.fixture
def client(model_registry: ModelRegistry, geo_service: GeoService) -> TestClient:
    """
    Возвращает TestClient с переопределёнными зависимостями.
    Это позволяет избежать любых побочных эффектов при запуске (БД, реальный геокодер и т.д.),
    """
    from app.main import create_app
    from app.ml.model_registry import get_model_registry
    from app.services.geo_service import get_geo_service

    app = create_app()
    app.dependency_overrides[get_model_registry] = lambda: model_registry
    app.dependency_overrides[get_geo_service] = lambda: geo_service

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def client_no_model(empty_registry: ModelRegistry, geo_service: GeoService) -> TestClient:
    """TestClient, в котором в реестре моделей не загружена ни одна модель."""
    from app.main import create_app
    from app.ml.model_registry import get_model_registry
    from app.services.geo_service import get_geo_service

    app = create_app()
    app.dependency_overrides[get_model_registry] = lambda: empty_registry
    app.dependency_overrides[get_geo_service] = lambda: geo_service

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Вспомогательные утилиты ──────────────────────────────────────────────────

# Вычисляем дату "завтра" с корректным переходом через конец месяца / года
TOMORROW = str(date.today().replace(day=date.today().day + 1)
               if date.today().day < 28
               else (date.today().replace(month=date.today().month + 1, day=1)
                     if date.today().month < 12
                     else date.today().replace(year=date.today().year + 1, month=1, day=1)))
