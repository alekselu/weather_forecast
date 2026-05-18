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
        params = {
            "city": "Moscow",
            "time": "2026-05-10",
            "params": ["temperature"],
        }
        response = client.get("/forecast", params=params)
        assert response.status_code == 200
        data = response.json()
        assert data["city"] == "Moscow"
        assert "coords" in data
        assert data["time"] == "2026-05-10"
