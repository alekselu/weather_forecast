"""Асинхронный клиент для обращения к ML-контейнеру."""

import httpx
from datetime import date
from pydantic import BaseModel
from fastapi import Request, HTTPException

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

    def sync_predict(self, req: PredictRequest, request: Request) -> ForecastPayload:
        print("State: ", vars(request.app.state))
        predictor: Predictor = request.app.state.predictor
        if not request.app.state.registry.is_ready():
            raise HTTPException(status_code=503, detail="Model not loaded yet")
        try:
            response = predictor.predict(req)
            return ForecastPayload(**response.model_dump_json())
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    async def health(self) -> dict:
        response = await self._client.get("/health")
        response.raise_for_status()
        return response.json()
