from fastapi import FastAPI, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Annotated, Dict
from app import db
from datetime import date
from app.core.logging import setup_logging
from app.utils.geolocation import GeoCoder, get_geo_coder
from app.schemas.forecast import ErrorResponse, ForecastResponse, HealthResponse
from app.ml.model_registry import ModelRegistry, get_model_registry
from app.services.forecast_service import ForecastService


setup_logging()
import logging

logger = logging.getLogger(__name__)

app = FastAPI()

origins = ["http://localhost:3000", "http://localhost:5173"]  # Example: React app

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

geocoder = GeoCoder()

# ── Dependency factories ─────────────────────────────────────────────────────


def get_forecast_service(
    geo: Annotated[GeoCoder, Depends(get_geo_coder)],
    registry: Annotated[ModelRegistry, Depends(get_model_registry)],
) -> ForecastService:
    return ForecastService(geo_coder=geo, model_registry=registry)


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
    return result.to_dict()


# Example: GET /forecast?time=2026-05-06&params=temperature&params=humidity&params=wind
@app.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Get weather forecast for a city",
    responses={
        200: {"description": "Successful forecast", "model": ForecastResponse},
        400: {"description": "Invalid input", "model": ErrorResponse},
        404: {"description": "City not found", "model": ErrorResponse},
        503: {"description": "Model not available", "model": ErrorResponse},
    },
)
async def get_forecast(
    time: Annotated[date, Query()],
    city: Annotated[str, Query()],
    geocoder: Annotated[GeoCoder, Depends(get_geo_coder)],
    country_code: str = "ru",
    params: list[str] = Query(),
) -> dict[str, Any]:
    """Retrieve weather forecast for a specified city and date.

    This endpoint accepts query parameters to get forecast data including
    geographical coordinates and requested weather parameters for the given
    location and time.

    Parameters
    ----------
    time : Annotated[date, Query()]
        The date for which the forecast is requested (format: YYYY-MM-DD).
    city : Annotated[str, Query()]
        The name of the city to get the forecast for.
    country_code : str, default="ru"
        Defaults to 'ru' if not provided.
    params : list[str], default=[]
        A list of weather parameters in accordance with Open-Meteo format to include in the forecast
        (e.g., 'temperature_2m_mean'). Can be specified multiple times.

    Returns
    -------
    dict[str, Any]
        A dictionary containing:
        - 'time': The requested forecast date
        - 'city': The city name
        - 'coords': Either geographical coordinates as a string if found,
          or an error message if location fetch failed
        - 'country_code': The country code used
        - 'params': The list of requested weather parameters
    """
    result: Dict[str, Any] = {}
    result: Dict[str, Any] = {
        "time": time,
        "city": city,
        "country_code": country_code,
        "params": params,
        "payload": {},
    }
    try:
        coords = await geocoder.fetch_location(city, country_code)
        result["coords"] = str(coords)
    except Exception as e:
        result["coords"] = str(e)
    return ForecastResponse(**result)
