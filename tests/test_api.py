"""
Интеграционные тесты для FastAPI эндпоинтов.
Использует TestClient с переопределением зависимостей — без реальной БД или геокодера.
"""

from datetime import date, timedelta

import pytest


TOMORROW = str(date.today() + timedelta(days=1))


class TestForecastEndpoint:
    """GET /forecast"""

    def test_happy_path_default_date(self, client):
        """Счастливый путь: дата по умолчанию (завтра)."""
        response = client.get("/forecast", params={"city": "Moscow"})
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Moscow"
        assert "avg_temperature_c" in data
        assert isinstance(data["avg_temperature_c"], float)
        assert "model_version" in data
        assert data["date"] == TOMORROW

    def test_happy_path_explicit_date(self, client):
        """Счастливый путь: явно указанная дата."""
        response = client.get("/forecast", params={"city": "Moscow", "date": "2026-07-15"})
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-07-15"

    def test_saint_petersburg(self, client):
        """Проверка работы с Санкт-Петербургом."""
        response = client.get("/forecast", params={"city": "Saint Petersburg"})
        assert response.status_code == 200
        assert response.json()["city"] == "Saint Petersburg"

    def test_city_not_found_returns_404(self, client):
        """Несуществующий город возвращает 404."""
        response = client.get("/forecast", params={"city": "NoSuchCityEverXYZ"})
        assert response.status_code == 404
        body = response.json()
        # FastAPI оборачивает детали HTTPException в {"detail": ...}
        detail = body.get("detail", body)
        assert detail["code"] == "CITY_NOT_FOUND"

    def test_missing_city_param_returns_422(self, client):
        """Отсутствие обязательного параметра city возвращает 422."""
        response = client.get("/forecast")
        assert response.status_code == 422

    def test_empty_city_string_returns_422_or_400(self, client):
        """Пустая строка города возвращает 422 или 400."""
        response = client.get("/forecast", params={"city": "   "})
        assert response.status_code in (400, 422)

    def test_invalid_date_format_returns_422(self, client):
        """Неверный формат даты возвращает 422."""
        response = client.get("/forecast", params={"city": "Moscow", "date": "not-a-date"})
        assert response.status_code == 422

    def test_model_not_available_returns_503(self, client_no_model):
        """Модель недоступна — возвращает 503."""
        response = client_no_model.get("/forecast", params={"city": "Moscow"})
        assert response.status_code == 503
        detail = response.json().get("detail", response.json())
        assert detail["code"] == "MODEL_UNAVAILABLE"

    def test_response_schema(self, client):
        """Проверка наличия всех ожидаемых полей в ответе."""
        response = client.get("/forecast", params={"city": "Kazan"})
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) >= {"city", "date", "avg_temperature_c", "model_version"}

    def test_temperature_is_plausible(self, client):
        """Проверка на правдоподобие: температура должна быть в диапазоне [-60, 60]°C."""
        response = client.get("/forecast", params={"city": "Novosibirsk", "date": "2026-01-15"})
        assert response.status_code == 200
        temp = response.json()["avg_temperature_c"]
        assert -60 <= temp <= 60


class TestHealthEndpoint:
    """GET /health — проверка работоспособности."""

    def test_returns_ok(self, client):
        """Стандартный сценарий: всё работает."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True
        assert data["model_version"] == "stub-v0"

    def test_model_not_loaded(self, client_no_model):
        """Модель не загружена."""
        response = client_no_model.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["model_loaded"] is False


class TestAPIVersioning:
    """Эндпоинты доступны как в корне, так и через префикс /api/v1."""

    def test_v1_prefix(self, client):
        """Доступ через префикс /api/v1."""
        response = client.get("/api/v1/forecast", params={"city": "Moscow"})
        assert response.status_code == 200

    def test_root_path(self, client):
        """Доступ через корневой путь."""
        response = client.get("/forecast", params={"city": "Moscow"})
        assert response.status_code == 200


class TestDocsEndpoint:
    """Тесты документации API."""

    def test_openapi_schema_accessible(self, client):
        """Проверка доступности OpenAPI схемы."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
