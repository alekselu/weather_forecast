"""
Интеграционные тесты ML-эндпоинтов (внутри того же FastAPI-приложения).

Эндпоинты: POST /predict, GET /health, POST /retrain.

Что мокируется:
  - ModelRegistry → FakeRegistry* из conftest
  - Trainer → FakeTrainer (не запускает реальное обучение)
  - Predictor.predict → возвращает детерминированный DataFrame-результат

Реальное обучение и Postgres не нужны.
"""
from __future__ import annotations

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient

from conftest import FakeRegistryReady, FakeRegistryNotReady, FakeRegistryRetraining


# ── Дополнительные фейки, специфичные для ML-тестов ────────────────────────


class FakeTrainer:
    """Не запускает реальное обучение; фиксирует факт вызова."""

    called: bool = False
    should_report_running: bool = False

    async def run(self) -> None:
        self.called = True


def fake_predict_response(daily_keys=(), hourly_keys=(), n_daily=7, n_hourly=72):
    """Строит ForecastPayload-подобный dict с нужным количеством значений."""
    return {
        "daily": {k: [float(i) for i in range(n_daily)] for k in daily_keys},
        "hourly": {k: [float(i) for i in range(n_hourly)] for k in hourly_keys},
    }


# ── Фикстуры HTTP-клиентов для ML-эндпоинтов ───────────────────────────────


@pytest_asyncio.fixture
async def ml_client_ready(fake_geocoder):
    from app.main import app
    from app.dependencies import get_geo_coder, get_model_registry

    reg = FakeRegistryReady()
    app.dependency_overrides[get_geo_coder] = lambda: fake_geocoder
    app.dependency_overrides[get_model_registry] = lambda: reg

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def ml_client_not_ready(fake_geocoder):
    from app.main import app
    from app.dependencies import get_geo_coder, get_model_registry

    reg = FakeRegistryNotReady()
    app.dependency_overrides[get_geo_coder] = lambda: fake_geocoder
    app.dependency_overrides[get_model_registry] = lambda: reg

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def ml_client_retraining(fake_geocoder):
    from app.main import app
    from app.dependencies import get_geo_coder, get_model_registry

    reg = FakeRegistryRetraining()
    app.dependency_overrides[get_geo_coder] = lambda: fake_geocoder
    app.dependency_overrides[get_model_registry] = lambda: reg

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ── Payload-примеры для /predict ───────────────────────────────────────────

DAILY_PREDICT_PAYLOAD = {
    "latitude": 55.75,
    "longitude": 37.62,
    "start_date": "2025-01-01",
    "end_date": "2025-01-07",
    "hourly": [],
    "daily": ["temperature_2m_mean", "temperature_2m_max"],
}

HOURLY_PREDICT_PAYLOAD = {
    **DAILY_PREDICT_PAYLOAD,
    "end_date": "2025-01-03",  # 3 дня × 24 = 72 часа
    "hourly": ["temperature_2m", "precipitation"],
    "daily": [],
}

COMBO_PREDICT_PAYLOAD = {
    **DAILY_PREDICT_PAYLOAD,
    "hourly": ["temperature_2m"],
    "daily": ["temperature_2m_mean"],
}


# ═══════════════════════════════════════════════════════════════════════════
# GET /health
# ═══════════════════════════════════════════════════════════════════════════


class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_returns_200(self, ml_client_ready):
        assert (await ml_client_ready.get("/health")).status_code == 200

    @pytest.mark.asyncio
    async def test_model_loaded_true_when_ready(self, ml_client_ready):
        body = (await ml_client_ready.get("/health")).json()
        assert body["model_loaded"] is True

    @pytest.mark.asyncio
    async def test_status_ok_when_ready(self, ml_client_ready):
        body = (await ml_client_ready.get("/health")).json()
        assert body["status"] == "ok"

    @pytest.mark.asyncio
    async def test_model_loaded_false_when_not_ready(self, ml_client_not_ready):
        body = (await ml_client_not_ready.get("/health")).json()
        assert body["model_loaded"] is False

    @pytest.mark.asyncio
    async def test_status_no_model_when_not_ready(self, ml_client_not_ready):
        body = (await ml_client_not_ready.get("/health")).json()
        assert body["status"] == "no_model"

    @pytest.mark.asyncio
    async def test_version_present_in_response(self, ml_client_ready):
        body = (await ml_client_ready.get("/health")).json()
        assert "model_version" in body
        assert body["model_version"] == "test-v1"

    @pytest.mark.asyncio
    async def test_retraining_now_false_by_default(self, ml_client_ready):
        body = (await ml_client_ready.get("/health")).json()
        assert body["retraining_now"] is False

    @pytest.mark.asyncio
    async def test_retraining_now_true_during_retrain(self, ml_client_retraining):
        body = (await ml_client_retraining.get("/health")).json()
        assert body["retraining_now"] is True


# ═══════════════════════════════════════════════════════════════════════════
# POST /predict
# ═══════════════════════════════════════════════════════════════════════════


class TestPredictEndpoint:

    # ── 200 / корректные данные ─────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_daily_returns_200(self, ml_client_ready):
        resp = await ml_client_ready.post("/predict", json=DAILY_PREDICT_PAYLOAD)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_daily_payload_contains_requested_params(self, ml_client_ready):
        resp = await ml_client_ready.post("/predict", json=DAILY_PREDICT_PAYLOAD)
        body = resp.json()
        for p in DAILY_PREDICT_PAYLOAD["daily"]:
            assert p in body["daily"], f"{p} отсутствует в ответе daily"

    @pytest.mark.asyncio
    async def test_daily_series_length_matches_day_range(self, ml_client_ready):
        """start=Jan1, end=Jan7 → 7 дней → 7 значений."""
        resp = await ml_client_ready.post("/predict", json=DAILY_PREDICT_PAYLOAD)
        body = resp.json()
        assert len(body["daily"]["temperature_2m_mean"]) == 7

    @pytest.mark.asyncio
    async def test_hourly_returns_200(self, ml_client_ready):
        resp = await ml_client_ready.post("/predict", json=HOURLY_PREDICT_PAYLOAD)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_hourly_payload_contains_requested_params(self, ml_client_ready):
        resp = await ml_client_ready.post("/predict", json=HOURLY_PREDICT_PAYLOAD)
        body = resp.json()
        for p in HOURLY_PREDICT_PAYLOAD["hourly"]:
            assert p in body["hourly"], f"{p} отсутствует в ответе hourly"

    @pytest.mark.asyncio
    async def test_hourly_series_length_matches_hours(self, ml_client_ready):
        """start=Jan1, end=Jan3 → 3 дня → 72 часа."""
        resp = await ml_client_ready.post("/predict", json=HOURLY_PREDICT_PAYLOAD)
        body = resp.json()
        assert len(body["hourly"]["temperature_2m"]) == 72

    @pytest.mark.asyncio
    async def test_combo_returns_both_keys_populated(self, ml_client_ready):
        resp = await ml_client_ready.post("/predict", json=COMBO_PREDICT_PAYLOAD)
        body = resp.json()
        assert "temperature_2m" in body["hourly"]
        assert "temperature_2m_mean" in body["daily"]

    @pytest.mark.asyncio
    async def test_only_daily_has_empty_hourly_in_response(self, ml_client_ready):
        resp = await ml_client_ready.post("/predict", json=DAILY_PREDICT_PAYLOAD)
        assert resp.json()["hourly"] == {}

    @pytest.mark.asyncio
    async def test_only_hourly_has_empty_daily_in_response(self, ml_client_ready):
        resp = await ml_client_ready.post("/predict", json=HOURLY_PREDICT_PAYLOAD)
        assert resp.json()["daily"] == {}

    # ── Ошибки ─────────────────────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_model_not_ready_returns_503(self, ml_client_not_ready):
        resp = await ml_client_not_ready.post("/predict", json=DAILY_PREDICT_PAYLOAD)
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_start_after_end_returns_422(self, ml_client_ready):
        """Pydantic model_validator отклоняет start > end."""
        payload = {
            **DAILY_PREDICT_PAYLOAD,
            "start_date": "2025-01-07",
            "end_date": "2025-01-01",
        }
        resp = await ml_client_ready.post("/predict", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_both_lists_returns_422(self, ml_client_ready):
        """Оба списка пусты — model_validator должен отклонить."""
        payload = {**DAILY_PREDICT_PAYLOAD, "hourly": [], "daily": []}
        resp = await ml_client_ready.post("/predict", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_coordinates_returns_422(self, ml_client_ready):
        payload = {
            "start_date": "2025-01-01",
            "end_date": "2025-01-03",
            "daily": ["temperature_2m_mean"],
        }
        resp = await ml_client_ready.post("/predict", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_date_string_returns_422(self, ml_client_ready):
        payload = {**DAILY_PREDICT_PAYLOAD, "start_date": "not-a-date"}
        resp = await ml_client_ready.post("/predict", json=payload)
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# POST /retrain
# ═══════════════════════════════════════════════════════════════════════════


class TestRetrainEndpoint:
    @pytest.mark.asyncio
    async def test_retrain_returns_200(self, ml_client_ready):
        from app.main import app
        from app.dependencies import get_trainer

        fake_trainer = FakeTrainer()
        app.dependency_overrides[get_trainer] = lambda: fake_trainer
        try:
            resp = await ml_client_ready.post("/retrain")
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(get_trainer, None)

    @pytest.mark.asyncio
    async def test_retrain_response_has_status_field(self, ml_client_ready):
        from app.main import app
        from app.dependencies import get_trainer

        app.dependency_overrides[get_trainer] = lambda: FakeTrainer()
        try:
            body = (await ml_client_ready.post("/retrain")).json()
            assert "status" in body
        finally:
            app.dependency_overrides.pop(get_trainer, None)

    @pytest.mark.asyncio
    async def test_retrain_triggers_trainer_run(self, ml_client_ready):
        """BackgroundTask вызывает trainer.run() — проверяем через флаг."""
        from app.main import app
        from app.dependencies import get_trainer

        fake_trainer = FakeTrainer()
        app.dependency_overrides[get_trainer] = lambda: fake_trainer
        try:
            await ml_client_ready.post("/retrain")
            await asyncio.sleep(0)  # одна итерация event loop для BackgroundTask
            assert fake_trainer.called is True
        finally:
            app.dependency_overrides.pop(get_trainer, None)

    @pytest.mark.asyncio
    async def test_retrain_while_running_returns_already_running(
        self, ml_client_retraining
    ):
        """
        Когда registry.retraining == True, ответ должен содержать
        status='already_running' вместо запуска нового обучения.
        """
        from app.main import app
        from app.dependencies import get_trainer

        fake_trainer = FakeTrainer()
        app.dependency_overrides[get_trainer] = lambda: fake_trainer
        try:
            body = (await ml_client_retraining.post("/retrain")).json()
            assert body["status"] == "already_running"
        finally:
            app.dependency_overrides.pop(get_trainer, None)

    @pytest.mark.asyncio
    async def test_retrain_does_not_call_trainer_when_already_running(
        self, ml_client_retraining
    ):
        """trainer.run() не должен вызываться, если переобучение уже идёт."""
        from app.main import app
        from app.dependencies import get_trainer

        fake_trainer = FakeTrainer()
        app.dependency_overrides[get_trainer] = lambda: fake_trainer
        try:
            await ml_client_retraining.post("/retrain")
            await asyncio.sleep(0)
            assert fake_trainer.called is False
        finally:
            app.dependency_overrides.pop(get_trainer, None)
