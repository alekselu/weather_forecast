import httpx
from fastapi import FastAPI, Query, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Annotated, Dict
from app import db
from datetime import date
from app.core.logging import setup_logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.schemas.forecast import (
    ErrorResponse,
    ForecastResponse,
    ForecastPayload,
    PredictRequest,
    PredictResponse,
)
from app.params import classify_params
from app.utils.structures import City
from app.clients.ml_client import MLClient, MLPredictRequest
from app.utils.geolocation import GeoCoder, get_geo_coder
from app.dependencies import get_ml_client
from app.ml.registry import ModelRegistry
from app.ml.trainer import Trainer
from app.ml.predictor import Predictor
from app.ml.routers import predict, health, retrain
from app.config import settings

setup_logging()
import logging

logger = logging.getLogger(__name__)

registry = ModelRegistry()
trainer = Trainer(registry, model_path=settings.MODEL_PATH)
predictor = Predictor(registry)
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.registry = registry
    app.state.predictor = predictor
    app.state.trainer = trainer
    # ── Start ──────────────────────────────────────────────────────────────
    import os

    ensemble_pkl = os.path.join(settings.MODEL_PATH, "ensemble.pkl")
    if os.path.exists(ensemble_pkl):
        await registry.load_from_disk(settings.MODEL_PATH)
    else:
        await trainer.run()
    # ── Retraining scheduler ────────────────────────────────────────────
    scheduler.add_job(
        trainer.run,
        trigger="cron",
        hour=settings.RETRAIN_HOUR,  # e.g. 2 (02:00 UTC)
        minute=settings.RETRAIN_MINUTE,  # e.g. 0
        id="retrain",
        replace_existing=True,
    )
    scheduler.start()
    yield
    # ── Stopping ──────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    client = get_ml_client()
    await client.aclose()


app = FastAPI(title="Weather Forecast Service", lifespan=lifespan)

app.include_router(predict.router)
app.include_router(health.router)
app.include_router(retrain.router)

origins = ["http://localhost:3000", "http://localhost:5173"]  # Example: React app

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

geocoder = GeoCoder()


# ── Endpoints ────────────────────────────────────────────────────────────────


@app.get(
    "/",
    summary="App standup check",
)
def root():
    return {"message": "API is up"}


@app.get(
    "/health/db",
    summary="DB accessibility check",
)
def check_db() -> dict[str, Any]:
    result: db.DatabaseHealthResponse = db.check_db()
    return {"res": "extra", **result.to_dict()}


# Example: GET /forecast?time=2026-05-06&params=temperature&params=humidity&params=wind
@app.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Get weather forecast for a city",
    responses={
        200: {"description": "Successful forecast", "model": ForecastResponse},
        400: {"description": "Invalid input", "model": ErrorResponse},
        404: {"description": "City not found", "model": ErrorResponse},
        503: {"description": "ML model unavailable", "model": ErrorResponse},
    },
)
async def get_forecast(
    city: Annotated[str, Query(description="City name")],
    params: Annotated[list[str], Query(description="Open-Meteo parameter names")] = [],
    start_date: Annotated[
        date | None, Query(description="Start of forecast range (YYYY-MM-DD)")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="End of forecast range (YYYY-MM-DD)")
    ] = None,
    time: Annotated[
        date | None,
        Query(deprecated=True, description="Deprecated. Use start_date/end_date."),
    ] = None,
    country_code: str = "ru",
    geocoder: Annotated[GeoCoder, Depends(get_geo_coder)] = ...,
    ml_client: Annotated[MLClient, Depends(get_ml_client)] = ...,
) -> ForecastResponse:
    """Retrieve weather forecast for a specified city and date.

    This endpoint accepts query parameters to get forecast data including
    geographical coordinates and requested weather parameters for the given
    location and time.
    """
    # ── 1. Normalization time → (start_date, end_date) ──────────────────────
    if time is not None and start_date is None and end_date is None:
        start_date = end_date = time

    if start_date is None or end_date is None:
        raise HTTPException(
            status_code=400,
            detail="Provide start_date and end_date (or the deprecated time parameter).",
        )
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be ≤ end_date.")

    # ── 2. Param classification ─────────────────────────────────────────
    hourly_params, daily_params, unknown = classify_params(params)
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown params: {unknown}")

    # ── 3. Geocoding ───────────────────────────────────────────────────
    try:
        coords = await geocoder.fetch_location_from(City(city, country_code))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Geocoder error: {e}")

    # ── 4. ML container query ───────────────────────────────────────────
    ml_request = MLPredictRequest(
        latitude=coords.latitude,
        longitude=coords.longitude,
        start_date=start_date,
        end_date=end_date,
        hourly=hourly_params,
        daily=daily_params,
    )
    predict_request = PredictRequest(
        latitude=coords.latitude,
        longitude=coords.longitude,
        start_date=start_date,
        end_date=end_date,
        hourly=hourly_params,
        daily=daily_params,
    )
    try:
        payload: ForecastPayload = await ml_client.predict(ml_request)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 503:
            raise HTTPException(status_code=503, detail="ML model is not available.")
        raise HTTPException(status_code=502, detail=f"ML service error: {e}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"ML service unreachable: {e}")

    # ── 5. Response ──────────────────────────────────────────────────────────
    return ForecastResponse(
        start_date=start_date,
        end_date=end_date,
        city=city,
        country_code=country_code,
        params=params,
        coords=str(coords),
        payload=payload,
    )


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest, request: Request) -> PredictResponse:
    print("Reached predict endpoint")
    predictor = request.app.state.predictor
    if not request.app.state.registry.is_ready():
        raise HTTPException(status_code=503, detail="Model not loaded yet")
    try:
        return predictor.predict(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
