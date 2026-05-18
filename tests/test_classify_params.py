"""
Unit tests for app/params.py :: classify_params.

Do not require a running application, network, or CSV.
All tests are synchronous — classify_params is a pure function.

Does NOT duplicate:
  - model tests (fit-predict)
  - /forecast response structure tests
"""
import pytest

from app.params import DAILY_PARAMS, HOURLY_PARAMS, classify_params


# ── dictionary invariants ──────────────────────────────────────────────────


class TestParamSetsIntegrity:
    def test_hourly_set_is_not_empty(self):
        assert len(HOURLY_PARAMS) > 0

    def test_daily_set_is_not_empty(self):
        assert len(DAILY_PARAMS) > 0

    def test_no_overlap_between_sets(self):
        """A parameter cannot be both hourly and daily simultaneously."""
        overlap = HOURLY_PARAMS & DAILY_PARAMS
        assert overlap == frozenset(), f"Overlap: {overlap}"

    def test_temperature_2m_is_hourly(self):
        """Smoke test: the most common hourly parameter should be in the dictionary."""
        assert "temperature_2m" in HOURLY_PARAMS

    def test_temperature_2m_mean_is_daily(self):
        assert "temperature_2m_mean" in DAILY_PARAMS


# ── hourly only ───────────────────────────────────────────────────────────


class TestClassifyHourlyOnly:
    def test_single_known_hourly(self):
        h, d, u = classify_params(["temperature_2m"])
        assert h == ["temperature_2m"] and d == [] and u == []

    def test_multiple_hourly(self):
        params = ["temperature_2m", "precipitation", "wind_speed_10m"]
        h, d, u = classify_params(params)
        assert set(h) == set(params) and d == [] and u == []

    def test_all_hourly_params_classified_correctly(self):
        all_h = list(HOURLY_PARAMS)
        h, d, u = classify_params(all_h)
        assert len(h) == len(all_h) and d == [] and u == []


# ── daily only ────────────────────────────────────────────────────────────


class TestClassifyDailyOnly:
    def test_single_known_daily(self):
        h, d, u = classify_params(["temperature_2m_mean"])
        assert h == [] and d == ["temperature_2m_mean"] and u == []

    def test_multiple_daily(self):
        params = ["temperature_2m_mean", "temperature_2m_max", "precipitation_sum"]
        h, d, u = classify_params(params)
        assert set(d) == set(params) and h == [] and u == []

    def test_all_daily_params_classified_correctly(self):
        all_d = list(DAILY_PARAMS)
        h, d, u = classify_params(all_d)
        assert len(d) == len(all_d) and h == [] and u == []


# ── combination ─────────────────────────────────────────────────────────────


class TestClassifyMixed:
    def test_one_hourly_one_daily(self):
        h, d, u = classify_params(["temperature_2m", "temperature_2m_mean"])
        assert "temperature_2m" in h
        assert "temperature_2m_mean" in d
        assert u == []

    def test_combo_with_unknown(self):
        h, d, u = classify_params(["temperature_2m", "temperature_2m_mean", "garbage"])
        assert "temperature_2m" in h
        assert "temperature_2m_mean" in d
        assert u == ["garbage"]

    def test_input_order_preserved_within_groups(self):
        """Order of elements within each group matches the input list."""
        params = [
            "temperature_2m",
            "precipitation",
            "temperature_2m_mean",
            "precipitation_sum",
        ]
        h, d, _ = classify_params(params)
        assert h == ["temperature_2m", "precipitation"]
        assert d == ["temperature_2m_mean", "precipitation_sum"]


# ── edge cases ────────────────────────────────────────────────────────


class TestClassifyEdgeCases:
    def test_empty_list_returns_three_empty_lists(self):
        h, d, u = classify_params([])
        assert h == [] and d == [] and u == []

    def test_all_unknown_params(self):
        h, d, u = classify_params(["fake_a", "fake_b"])
        assert h == [] and d == [] and set(u) == {"fake_a", "fake_b"}

    def test_duplicate_param_appears_twice_in_group(self):
        """Duplicates are not collapsed — deduplication is the caller's responsibility."""
        h, _, _ = classify_params(["temperature_2m", "temperature_2m"])
        assert len(h) == 2

    def test_case_sensitive_unknown(self):
        """Open-Meteo parameters are case-sensitive: 'Temperature_2m' is unknown."""
        _, _, u = classify_params(["Temperature_2m"])
        assert "Temperature_2m" in u

    def test_returns_tuple_of_three_lists(self):
        result = classify_params(["temperature_2m"])
        assert isinstance(result, tuple) and len(result) == 3
        assert all(isinstance(g, list) for g in result)
