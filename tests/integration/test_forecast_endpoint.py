"""
Интеграционные тесты GET /forecast.

Новый функционал (не покрытый существующими тестами структуры ответа):
  - Диапазон дат (start_date / end_date) вместо одиночного time
  - Алиас time → спан длиной 1
  - Приоритет start_date/end_date над time
  - Только daily / только hourly / комбо в payload
  - Длины временны́х рядов соответствуют диапазону
  - Валидация: start_date > end_date → 400
  - Валидация: нет дат → 400
  - Валидация: только start без end → 400
  - Валидация: неизвестный params → 400
  - Несуществующий город → 404
  - Модель не загружена → 503

Фикстуры: conftest.py (client, client_no_model, fake_geocoder, ...)
"""
from __future__ import annotations

import pytest
from app.utils.utils import build_forecast_url

# ═══════════════════════════════════════════════════════════════════════════
# Диапазон дат — новый API
# ═══════════════════════════════════════════════════════════════════════════


class TestDateRangeAPI:
    @pytest.mark.asyncio
    async def test_start_end_date_returns_200(self, client, valid_daily_params):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-07",
            params=valid_daily_params,
        )
        resp = await client.get(url)
        print(resp.status_code)
        print(resp.text)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_response_echoes_start_date(self, client, valid_daily_params):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-07",
            params=valid_daily_params,
        )
        body = (await client.get(url)).json()
        assert body["start_date"] == "2025-01-01"

    @pytest.mark.asyncio
    async def test_response_echoes_end_date(self, client, valid_daily_params):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-07",
            params=valid_daily_params,
        )
        body = (await client.get(url)).json()
        assert body["end_date"] == "2025-01-07"

    @pytest.mark.asyncio
    async def test_single_day_range_allowed(self, client, valid_daily_params):
        """start_date == end_date — допустимо."""
        url = build_forecast_url(
            start_date="2025-06-15",
            end_date="2025-06-15",
            params=valid_daily_params,
        )
        assert (await client.get(url)).status_code == 200

    @pytest.mark.asyncio
    async def test_response_contains_city(self, client, valid_daily_params):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=valid_daily_params,
        )
        body = (await client.get(url)).json()
        assert body["city"] == "Moscow"

    @pytest.mark.asyncio
    async def test_response_contains_coords(self, client, valid_daily_params):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=valid_daily_params,
        )
        body = (await client.get(url)).json()
        assert body.get("coords", "") != ""

    @pytest.mark.asyncio
    async def test_response_has_no_legacy_time_field(self, client, valid_daily_params):
        """Поле 'time' из старого API не должно присутствовать в ответе."""
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=valid_daily_params,
        )
        body = (await client.get(url)).json()
        assert "time" not in body


# ═══════════════════════════════════════════════════════════════════════════
# Алиас time (обратная совместимость)
# ═══════════════════════════════════════════════════════════════════════════


class TestTimeAlias:
    @pytest.mark.asyncio
    async def test_time_param_returns_200(self, client, valid_daily_params):
        url = build_forecast_url(time="2025-03-10", params=valid_daily_params)
        assert (await client.get(url)).status_code == 200

    @pytest.mark.asyncio
    async def test_time_sets_start_and_end_equal(self, client, valid_daily_params):
        url = build_forecast_url(time="2025-03-10", params=valid_daily_params)
        body = (await client.get(url)).json()
        assert body["start_date"] == "2025-03-10"
        assert body["end_date"] == "2025-03-10"

    @pytest.mark.asyncio
    async def test_start_end_takes_priority_over_time(self, client, valid_daily_params):
        """Если переданы и time, и start/end_date — применяется диапазон."""
        url = build_forecast_url(
            time="2025-01-01",
            start_date="2025-05-01",
            end_date="2025-05-07",
            params=valid_daily_params,
        )
        body = (await client.get(url)).json()
        assert body["start_date"] == "2025-05-01"
        assert body["end_date"] == "2025-05-07"

    @pytest.mark.asyncio
    async def test_time_alias_produces_single_day_payload(
        self, client, valid_daily_params
    ):
        """time=X → payload daily содержит ровно 1 значение на параметр."""
        url = build_forecast_url(time="2025-03-10", params=valid_daily_params)
        body = (await client.get(url)).json()
        for param in valid_daily_params:
            values = body["payload"]["daily"].get(param, [])
            assert (
                len(values) == 1
            ), f"{param}: ожидали 1 значение, получили {len(values)}"


# ═══════════════════════════════════════════════════════════════════════════
# Классификация параметров и структура payload
# ═══════════════════════════════════════════════════════════════════════════


class TestPayloadClassification:
    @pytest.mark.asyncio
    async def test_daily_params_land_in_daily_payload(self, client, valid_daily_params):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=valid_daily_params,
        )
        body = (await client.get(url)).json()
        for p in valid_daily_params:
            assert p in body["payload"]["daily"], f"{p} не найден в payload.daily"

    @pytest.mark.asyncio
    async def test_only_daily_request_has_empty_hourly(
        self, client, valid_daily_params
    ):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=valid_daily_params,
        )
        body = (await client.get(url)).json()
        assert body["payload"]["hourly"] == {}

    @pytest.mark.asyncio
    async def test_hourly_params_land_in_hourly_payload(
        self, client, valid_hourly_params
    ):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=valid_hourly_params,
        )
        body = (await client.get(url)).json()
        for p in valid_hourly_params:
            assert p in body["payload"]["hourly"], f"{p} не найден в payload.hourly"

    @pytest.mark.asyncio
    async def test_only_hourly_request_has_empty_daily(
        self, client, valid_hourly_params
    ):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=valid_hourly_params,
        )
        body = (await client.get(url)).json()
        assert body["payload"]["daily"] == {}

    @pytest.mark.asyncio
    async def test_combo_request_fills_both_payload_keys(
        self, client, valid_daily_params, valid_hourly_params
    ):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=valid_daily_params + valid_hourly_params,
        )
        body = (await client.get(url)).json()
        for p in valid_daily_params:
            assert p in body["payload"]["daily"]
        for p in valid_hourly_params:
            assert p in body["payload"]["hourly"]

    @pytest.mark.asyncio
    async def test_daily_series_length_matches_day_count(self, client):
        """7-дневный диапазон → 7 значений в daily-параметре."""
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-07",
            params=["temperature_2m_mean"],
        )
        body = (await client.get(url)).json()
        values = body["payload"]["daily"]["temperature_2m_mean"]
        assert len(values) == 7

    @pytest.mark.asyncio
    async def test_hourly_series_length_matches_hours(self, client):
        """3-дневный диапазон → 3×24 = 72 значения в hourly-параметре."""
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=["temperature_2m"],
        )
        body = (await client.get(url)).json()
        values = body["payload"]["hourly"]["temperature_2m"]
        assert len(values) == 72

    @pytest.mark.asyncio
    async def test_params_field_echoed_in_response(self, client, valid_daily_params):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=valid_daily_params,
        )
        body = (await client.get(url)).json()
        assert set(body["params"]) == set(valid_daily_params)


# ═══════════════════════════════════════════════════════════════════════════
# Ошибки валидации — 400 / 422
# ═══════════════════════════════════════════════════════════════════════════


class TestValidationErrors:
    @pytest.mark.asyncio
    async def test_start_after_end_returns_400(self, client, valid_daily_params):
        url = build_forecast_url(
            start_date="2025-01-07",
            end_date="2025-01-01",
            params=valid_daily_params,
        )
        assert (await client.get(url)).status_code == 400

    @pytest.mark.asyncio
    async def test_start_after_end_error_mentions_dates(
        self, client, valid_daily_params
    ):
        url = build_forecast_url(
            start_date="2025-01-07",
            end_date="2025-01-01",
            params=valid_daily_params,
        )
        detail = (await client.get(url)).json()["detail"].lower()
        assert "start_date" in detail or "end_date" in detail

    @pytest.mark.asyncio
    async def test_no_date_params_returns_400(self, client, valid_daily_params):
        url = build_forecast_url(params=valid_daily_params)
        assert (await client.get(url)).status_code == 400

    @pytest.mark.asyncio
    async def test_only_start_without_end_returns_400(self, client, valid_daily_params):
        url = build_forecast_url(start_date="2025-01-01", params=valid_daily_params)
        assert (await client.get(url)).status_code == 400

    @pytest.mark.asyncio
    async def test_only_end_without_start_returns_400(self, client, valid_daily_params):
        url = build_forecast_url(end_date="2025-01-07", params=valid_daily_params)
        assert (await client.get(url)).status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_param_returns_400(self, client):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=["totally_nonexistent_metric"],
        )
        assert (await client.get(url)).status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_param_error_names_the_param(self, client):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=["totally_nonexistent_metric"],
        )
        detail = (await client.get(url)).json()["detail"]
        assert "totally_nonexistent_metric" in detail

    @pytest.mark.asyncio
    async def test_invalid_date_format_returns_422(self, client, valid_daily_params):
        """FastAPI/Pydantic отклоняет невалидный формат даты с 422."""
        url = build_forecast_url(
            start_date="not-a-date",
            end_date="2025-01-07",
            params=valid_daily_params,
        )
        assert (await client.get(url)).status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
# Внешние ошибки — 404 и 503
# ═══════════════════════════════════════════════════════════════════════════


class TestExternalErrors:
    @pytest.mark.asyncio
    async def test_unknown_city_returns_404(self, client, valid_daily_params):
        """FakeGeoCoder.fetch_location_from('unknown') → LookupError → 404."""
        url = build_forecast_url(
            city="unknown",
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=valid_daily_params,
        )
        assert (await client.get(url)).status_code == 404

    @pytest.mark.asyncio
    async def test_model_not_loaded_returns_503(
        self, client_no_model, valid_daily_params
    ):
        url = build_forecast_url(
            start_date="2025-01-01",
            end_date="2025-01-03",
            params=valid_daily_params,
        )
        assert (await client_no_model.get(url)).status_code == 503
