"""Асинхронный клиент для обращения к ML-контейнеру."""
import httpx
from datetime import date
from pydantic import BaseModel

from app.schemas.forecast import ForecastPayload, PredictRequest
from app.ml.predictor import Predictor


class MLPredictRequest(BaseModel):
    latitude: float
    longitude: float
    start_date: date
    end_date: date
    hourly: list[str] = []
    daily: list[str] = []


class MLClient:
    def __init__(self, base_url: str) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def predict(self, request: MLPredictRequest) -> ForecastPayload:
        print("Inside MLClient::predict", type(self._client))
        response = await self._client.post(
            "/predict",
            json=request.model_dump(mode="json"),
        )
        response.raise_for_status()
        return ForecastPayload(**response.json())

    def sync_predict(
        self, request: PredictRequest, predictor: Predictor
    ) -> ForecastPayload:
        pass

    async def health(self) -> dict:
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()
