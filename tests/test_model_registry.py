"""Unit tests for ModelRegistry and ModelStub."""

from datetime import date

import pytest

from app.core.exceptions import ModelNotAvailableError
from app.ml.model_registry import FeatureVector, ModelRegistry, ModelStub


def _make_features(
    city: str = "Saint Petersburg",
    lat: float = 59.93,
    lon: float = 30.34,
    forecast_date: date | None = None,
    doy: int = 100,
    month: int = 4,
) -> FeatureVector:
    return FeatureVector(
        city=city,
        forecast_date=forecast_date or date(2026, 4, 10),
        lat=lat,
        lon=lon,
        day_of_year=doy,
        month=month,
        day_of_week=4,
    )


class TestModelStub:
    def test_version(self):
        stub = ModelStub()
        assert stub.version == "stub-v0"

    def test_is_ready(self):
        assert ModelStub().is_ready is True

    def test_predict_returns_float(self):
        stub = ModelStub()
        features = _make_features()
        result = stub.predict(features)
        assert isinstance(result, float)

    def test_predict_plausible_range(self):
        """Stub predictions should be in [-60, 60]°C."""
        stub = ModelStub()
        for lat, doy in [(59.93, 15), (59.93, 196), (55.76, 100), (0.0, 180)]:
            features = _make_features(lat=lat, doy=doy)
            temp = stub.predict(features)
            assert (
                -60 <= temp <= 60
            ), f"Implausible temp {temp} for lat={lat}, doy={doy}"

    def test_summer_warmer_than_winter_spb(self):
        """July should be warmer than January for Saint Petersburg."""
        stub = ModelStub()
        jan = _make_features(lat=59.93, doy=15)  # ~mid-January
        jul = _make_features(lat=59.93, doy=196)  # ~mid-July
        assert stub.predict(jul) > stub.predict(jan)

    def test_predict_deterministic(self):
        stub = ModelStub()
        f = _make_features()
        assert stub.predict(f) == stub.predict(f)


class TestModelRegistry:
    def test_not_ready_when_empty(self):
        reg = ModelRegistry()
        assert reg.is_ready is False

    def test_ready_after_load(self):
        reg = ModelRegistry()
        reg.load(ModelStub())
        assert reg.is_ready is True

    def test_version_after_load(self):
        reg = ModelRegistry()
        reg.load(ModelStub())
        assert reg.current_version == "stub-v0"

    def test_predict_raises_when_empty(self):
        reg = ModelRegistry()
        features = _make_features()
        with pytest.raises(ModelNotAvailableError):
            reg.predict(features)

    def test_predict_after_load(self):
        reg = ModelRegistry()
        reg.load(ModelStub())
        features = _make_features()
        result = reg.predict(features)
        assert isinstance(result, float)

    def test_hot_swap(self):
        """Swap should replace model atomically."""
        reg = ModelRegistry()
        reg.load(ModelStub())
        old_ver = reg.current_version

        class FakeModel(ModelStub):
            VERSION = "fake-v1"

        reg.swap(FakeModel())
        assert reg.current_version == "fake-v1"
        assert reg.current_version != old_ver
        # Registry should still be ready and produce predictions
        assert reg.is_ready
        assert isinstance(reg.predict(_make_features()), float)
