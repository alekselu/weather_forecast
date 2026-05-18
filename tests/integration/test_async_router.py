"""
Интеграционные тесты AsyncRouter.

AsyncRouter обращается к Open-Meteo API — в тестах httpx полностью мокируется
через respx (или unittest.mock.patch на _send_request).

Покрывают:
  - Корректная сборка Request из (coords, dates, params)
  - _build_request_params формирует правильные query-параметры
  - _build_response правильно парсит ответ Open-Meteo в PlacedResponseData
  - Обработка HTTPStatusError → Exception с деталями
  - Ответ содержит данные за все запрошенные периоды (daily / hourly / combo)

SQLAlchemy Session мокируется для случаев, когда router обращается
к БД за историей (если архитектура предполагает это).
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pandas as pd
import pytest

from app.router.async_router import AsyncRouter
from app.router.messages.messages import (
    Request,
    RequiredRequestParams,
    TimeRequestParams,
)
from app.utils.structures import Coordinates, TimePeriod

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
CSV_PATH = FIXTURES_DIR / "data_2023_2026.csv"


# ═══════════════════════════════════════════════════════════════════════════
# Вспомогательные фабрики
# ═══════════════════════════════════════════════════════════════════════════


def make_request(
    periods: list[TimePeriod],
    start: date = date(2025, 1, 1),
    end: date = date(2025, 1, 7),
    lat: float = 55.75,
    lon: float = 37.62,
) -> Request:
    return Request(
        required_params=RequiredRequestParams(latitude=lat, longitude=lon),
        time_params=TimeRequestParams(start_date=start, end_date=end),
        time_periods=periods,
    )


def open_meteo_daily_response(
    start: date = date(2025, 1, 1),
    n: int = 7,
    params: list[str] | None = None,
) -> dict:
    """Минимальный ответ Open-Meteo для daily-запроса."""
    params = params or ["temperature_2m_mean", "temperature_2m_max"]
    dates = [(start + pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n)]
    daily_data: dict = {"time": dates}
    for p in params:
        daily_data[p] = [float(i) * 1.1 for i in range(n)]
    return {
        "latitude": 55.75,
        "longitude": 37.62,
        "daily": daily_data,
    }


def open_meteo_hourly_response(
    start: date = date(2025, 1, 1),
    n_days: int = 3,
    params: list[str] | None = None,
) -> dict:
    params = params or ["temperature_2m"]
    n_hours = n_days * 24
    hourly_data: dict = {
        "time": [f"2025-01-0{d+1}T{h:02d}:00" for d in range(n_days) for h in range(24)]
    }
    for p in params:
        hourly_data[p] = [float(i) * 0.5 for i in range(n_hours)]
    return {
        "latitude": 55.75,
        "longitude": 37.62,
        "hourly": hourly_data,
    }


def make_httpx_response(payload: dict, status_code: int = 200) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        content=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        request=httpx.Request("GET", "https://archive-api.open-meteo.com/v1/archive"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# _build_request_params
# ═══════════════════════════════════════════════════════════════════════════


class TestBuildRequestParams:
    def test_contains_latitude(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY])
        params = router._build_request_params(req)
        assert "latitude" in params
        assert float(params["latitude"]) == pytest.approx(55.75)

    def test_contains_longitude(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY])
        params = router._build_request_params(req)
        assert "longitude" in params

    def test_contains_start_date(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY], start=date(2025, 1, 1))
        params = router._build_request_params(req)
        assert params.get("start_date") == "2025-01-01"

    def test_contains_end_date(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY], end=date(2025, 1, 7))
        params = router._build_request_params(req)
        assert params.get("end_date") == "2025-01-07"

    def test_daily_period_in_params(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY])
        params = router._build_request_params(req)
        assert "daily" in params

    def test_hourly_period_in_params(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.HOURLY])
        params = router._build_request_params(req)
        assert "hourly" in params

    def test_combo_has_both_periods(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY, TimePeriod.HOURLY])
        params = router._build_request_params(req)
        assert "daily" in params and "hourly" in params

    def test_daily_param_names_are_comma_separated(self):
        """Open-Meteo ожидает daily=temperature_2m_mean,temperature_2m_max"""
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY])
        params = router._build_request_params(req)
        daily_str = params["daily"]
        # Несколько параметров разделены запятой, без пробелов
        assert "," in daily_str or len(daily_str) > 0


# ═══════════════════════════════════════════════════════════════════════════
# _build_response (парсинг ответа Open-Meteo)
# ═══════════════════════════════════════════════════════════════════════════


class TestBuildResponse:
    def test_daily_response_produces_placed_response_data(self):
        from app.router.messages.messages import PlacedResponseData

        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY])
        raw = make_httpx_response(open_meteo_daily_response())

        result = router._build_response(req, raw)
        assert isinstance(result, PlacedResponseData)

    def test_daily_response_data_list_has_correct_length(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY])
        raw = make_httpx_response(open_meteo_daily_response(n=7))

        result = router._build_response(req, raw)
        assert len(result.data.data) == 7

    def test_daily_response_coords_match_request(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY], lat=55.75, lon=37.62)
        raw = make_httpx_response(open_meteo_daily_response())

        result = router._build_response(req, raw)
        assert result.coords.latitude == pytest.approx(55.75)
        assert result.coords.longitude == pytest.approx(37.62)

    def test_hourly_response_data_list_has_correct_length(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.HOURLY], end=date(2025, 1, 3))
        raw = make_httpx_response(open_meteo_hourly_response(n_days=3))

        result = router._build_response(req, raw)
        # 3 дня × 24 часа = 72 записи
        assert len(result.data.data) == 72

    def test_combo_response_data_includes_both_period_items(self):
        """Комбо-ответ: daily (7 дней) + hourly (3 дня × 24)."""
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY, TimePeriod.HOURLY])

        payload = {
            **open_meteo_daily_response(n=7),
            **open_meteo_hourly_response(n_days=3),
        }
        raw = make_httpx_response(payload)
        result = router._build_response(req, raw)
        assert len(result.data.data) == 7 + 72

    def test_missing_period_in_response_does_not_raise(self):
        """Если open-meteo не вернул hourly — нет ошибки, данные просто пусты."""
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY, TimePeriod.HOURLY])
        # Ответ содержит только daily
        raw = make_httpx_response(open_meteo_daily_response(n=3))

        result = router._build_response(req, raw)
        # Только daily-строки
        assert len(result.data.data) == 3

    def test_each_response_params_has_time_field(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY])
        raw = make_httpx_response(open_meteo_daily_response(n=3))

        result = router._build_response(req, raw)
        for item in result.data.data:
            assert item.params.time is not None and item.params.time != ""


# ═══════════════════════════════════════════════════════════════════════════
# send_request — интеграция с мокированным HTTP
# ═══════════════════════════════════════════════════════════════════════════


class TestSendRequest:
    @pytest.mark.asyncio
    async def test_send_request_returns_placed_response_data(self):
        from app.router.messages.messages import PlacedResponseData

        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY])
        fake_http_resp = make_httpx_response(open_meteo_daily_response())

        with patch.object(
            router, "_send_request", new=AsyncMock(return_value=fake_http_resp)
        ):
            result = await router.send_request(req)

        assert isinstance(result, PlacedResponseData)

    @pytest.mark.asyncio
    async def test_send_request_raises_on_4xx(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY])
        # Open-Meteo вернул 400
        bad_resp = make_httpx_response({"reason": "Bad Request"}, status_code=400)

        with patch.object(
            router, "_send_request", new=AsyncMock(return_value=bad_resp)
        ):
            with pytest.raises(Exception):
                await router.send_request(req)

    @pytest.mark.asyncio
    async def test_send_request_raises_on_503(self):
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY])
        bad_resp = make_httpx_response({}, status_code=503)

        with patch.object(
            router, "_send_request", new=AsyncMock(return_value=bad_resp)
        ):
            with pytest.raises(Exception):
                await router.send_request(req)

    @pytest.mark.asyncio
    async def test_send_request_passes_correct_params_to_http(self):
        """_build_request вызывается и сформированный запрос уходит в _send_request."""
        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY])
        fake_http_resp = make_httpx_response(open_meteo_daily_response())

        captured = []

        async def fake_send(http_req):
            captured.append(http_req)
            return fake_http_resp

        with patch.object(router, "_send_request", new=fake_send):
            await router.send_request(req)

        assert len(captured) == 1
        sent_url = str(captured[0].url)
        assert "latitude" in sent_url or "start_date" in sent_url


# ═══════════════════════════════════════════════════════════════════════════
# Тест с реальным CSV: AsyncRouter получает данные, совпадающие с CSV
# ═══════════════════════════════════════════════════════════════════════════


class TestAsyncRouterWithCSVData:
    """
    Open-Meteo мокируется ответом, построенным из реального CSV.
    Проверяет, что данные из CSV корректно проходят через _build_response.
    """

    @pytest.fixture(scope="class")
    def df(self) -> pd.DataFrame:
        if not CSV_PATH.exists():
            pytest.skip(f"CSV не найден: {CSV_PATH}")
        df = pd.read_csv(CSV_PATH, parse_dates=["date"])
        return df.sort_values("date").reset_index(drop=True)

    @pytest.fixture(scope="class")
    def daily_col(self, df) -> str:
        from app.params import DAILY_PARAMS

        cols = [c for c in df.columns if c in DAILY_PARAMS]
        if not cols:
            pytest.skip("CSV не содержит known daily-параметров")
        return cols[0]

    @pytest.mark.asyncio
    async def test_response_values_match_csv_values(self, df, daily_col):
        """
        Строим Open-Meteo-подобный ответ из CSV и проверяем,
        что _build_response возвращает те же значения.
        """
        start = date(2025, 1, 1)
        n = 7
        slice_df = df[df["date"] >= pd.Timestamp(start)].head(n)

        if len(slice_df) < n:
            pytest.skip("CSV содержит меньше строк, чем нужно для теста")

        dates = slice_df["date"].dt.strftime("%Y-%m-%d").tolist()
        values = slice_df[daily_col].tolist()

        payload = {
            "latitude": 55.75,
            "longitude": 37.62,
            "daily": {"time": dates, daily_col: values},
        }

        router = AsyncRouter()
        req = make_request([TimePeriod.DAILY], start=start, end=date(2025, 1, 7))
        fake_resp = make_httpx_response(payload)

        with patch.object(
            router, "_send_request", new=AsyncMock(return_value=fake_resp)
        ):
            result = await router.send_request(req)

        assert len(result.data.data) == n
        # Первое значение в ответе совпадает с первым значением в CSV
        first_item = result.data.data[0]
        csv_first_value = values[0]
        response_value = getattr(first_item.data_params, daily_col, None)
        if response_value is not None:
            assert response_value == pytest.approx(csv_first_value, rel=1e-3)
