from functools import lru_cache
from app.clients.ml_client import MLClient
from app.ml.registry import ModelRegistry
from app.utils.geolocation import get_geo_coder as _get_geo_coder, GeoCoder


@lru_cache
def get_ml_client() -> MLClient:
    from app.config import settings

    return MLClient(base_url=settings.ML_SERVICE_URL)


def get_model_registry() -> ModelRegistry:
    return ModelRegistry()


def get_geo_coder() -> GeoCoder:
    return _get_geo_coder()
