"""
API routes: GET /forecast, GET /health
"""

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.exceptions import (
    CityNotFoundError,
    InsufficientDataError,
    ModelNotAvailableError,
)
from app.ml.model_registry import ModelRegistry, get_model_registry
from app.schemas.forecast import ErrorResponse, ForecastResponse, HealthResponse
from app.services.forecast_service import ForecastService
from app.services.geo_service import GeoService, get_geo_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Dependency factories ─────────────────────────────────────────────────────


def get_forecast_service(
    geo: Annotated[GeoService, Depends(get_geo_service)],
    registry: Annotated[ModelRegistry, Depends(get_model_registry)],
) -> ForecastService:
    return ForecastService(geo_service=geo, model_registry=registry)


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Get temperature forecast for a city",
    responses={
        200: {"description": "Successful forecast", "model": ForecastResponse},
        400: {"description": "Invalid input", "model": ErrorResponse},
        404: {"description": "City not found", "model": ErrorResponse},
        503: {"description": "Model not available", "model": ErrorResponse},
    },
)
def get_forecast(
    city: Annotated[
        str,
        Query(
            min_length=1,
            max_length=100,
            description="City name (e.g. 'Saint Petersburg')",
            example="Saint Petersburg",
        ),
    ],
    forecast_date: Annotated[
        Optional[date],
        Query(
            alias="date",
            description="Target date (YYYY-MM-DD). Defaults to tomorrow.",
            example="2026-04-27",
        ),
    ] = None,
    service: ForecastService = Depends(get_forecast_service),
) -> ForecastResponse:
    """
    Return predicted average temperature (°C) for the given city.

    - **city**: city name string (geocoded via Nominatim)
    - **date**: optional forecast date; defaults to tomorrow

    Errors are returned as structured JSON with `error`, `detail`, `code` fields.
    """
    city = city.strip()
    if not city:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Validation error",
                "detail": "city must not be blank",
                "code": "INVALID_INPUT",
            },
        )

    try:
        return service.get_forecast(city=city, forecast_date=forecast_date)

    except CityNotFoundError as exc:
        logger.warning("city_not_found", city=exc.city)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "City not found",
                "detail": str(exc),
                "code": "CITY_NOT_FOUND",
            },
        )

    except ModelNotAvailableError as exc:
        logger.error("model_unavailable", reason=exc.reason)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "Model not available",
                "detail": str(exc),
                "code": "MODEL_UNAVAILABLE",
            },
        )

    except InsufficientDataError as exc:
        logger.warning(
            "insufficient_data",
            city=exc.city,
            required=exc.required_days,
            available=exc.available_days,
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "Insufficient historical data",
                "detail": str(exc),
                "code": "INSUFFICIENT_DATA",
            },
        )

    except Exception as exc:  # pragma: no cover
        logger.exception("unexpected_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "detail": "Unexpected error occurred",
                "code": "INTERNAL_ERROR",
            },
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
)
def health_check(
    registry: Annotated[ModelRegistry, Depends(get_model_registry)],
) -> HealthResponse:
    """Returns application health and model status."""
    return HealthResponse(
        status="ok",
        model_loaded=registry.is_ready,
        model_version=registry.current_version,
    )
