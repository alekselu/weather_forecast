"""
Integration tests for FastAPI endpoints.
Uses TestClient with dependency overrides — no real DB or geocoder.
"""

from datetime import date, timedelta

import pytest


TOMORROW = str(date.today() + timedelta(days=1))


class TestForecastEndpoint:
    """GET /forecast"""

    def test_happy_path_default_date(self, client):
        response = client.get("/forecast", params={"city": "Moscow"})
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Moscow"
        assert "avg_temperature_c" in data
        assert isinstance(data["avg_temperature_c"], float)
        assert "model_version" in data
        assert data["date"] == TOMORROW

    def test_happy_path_explicit_date(self, client):
        response = client.get(
            "/forecast", params={"city": "Moscow", "date": "2026-07-15"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-07-15"

    def test_saint_petersburg(self, client):
        response = client.get("/forecast", params={"city": "Saint Petersburg"})
        assert response.status_code == 200
        assert response.json()["city"] == "Saint Petersburg"

    def test_city_not_found_returns_404(self, client):
        response = client.get("/forecast", params={"city": "NoSuchCityEverXYZ"})
        assert response.status_code == 404
        body = response.json()
        # FastAPI wraps HTTPException detail inside {"detail": ...}
        detail = body.get("detail", body)
        assert detail["code"] == "CITY_NOT_FOUND"

    def test_missing_city_param_returns_422(self, client):
        response = client.get("/forecast")
        assert response.status_code == 422

    def test_empty_city_string_returns_422_or_400(self, client):
        response = client.get("/forecast", params={"city": "   "})
        assert response.status_code in (400, 422)

    def test_invalid_date_format_returns_422(self, client):
        response = client.get(
            "/forecast", params={"city": "Moscow", "date": "not-a-date"}
        )
        assert response.status_code == 422

    def test_model_not_available_returns_503(self, client_no_model):
        response = client_no_model.get("/forecast", params={"city": "Moscow"})
        assert response.status_code == 503
        detail = response.json().get("detail", response.json())
        assert detail["code"] == "MODEL_UNAVAILABLE"

    def test_response_schema(self, client):
        """Verify all expected fields are present in the response."""
        response = client.get("/forecast", params={"city": "Kazan"})
        assert response.status_code == 200
        data = response.json()
        assert set(data.keys()) >= {
            "city",
            "date",
            "avg_temperature_c",
            "model_version",
        }

    def test_temperature_is_plausible(self, client):
        """Sanity check: temperature should be in [-60, 60]°C range."""
        response = client.get(
            "/forecast", params={"city": "Novosibirsk", "date": "2026-01-15"}
        )
        assert response.status_code == 200
        temp = response.json()["avg_temperature_c"]
        assert -60 <= temp <= 60


class TestHealthEndpoint:
    """GET /health"""

    def test_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["model_loaded"] is True
        assert data["model_version"] == "stub-v0"

    def test_model_not_loaded(self, client_no_model):
        response = client_no_model.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["model_loaded"] is False


class TestAPIVersioning:
    """Endpoints are available both at root and under /api/v1."""

    def test_v1_prefix(self, client):
        response = client.get("/api/v1/forecast", params={"city": "Moscow"})
        assert response.status_code == 200

    def test_root_path(self, client):
        response = client.get("/forecast", params={"city": "Moscow"})
        assert response.status_code == 200


class TestDocsEndpoint:
    def test_openapi_schema_accessible(self, client):
        response = client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "paths" in schema
