from functools import lru_cache
from app.clients.ml_client import MLClient


@lru_cache
def get_ml_client() -> MLClient:
    from app.config import ML_SERVICE_URL

    return MLClient(base_url=ML_SERVICE_URL)
