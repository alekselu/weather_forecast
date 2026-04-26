"""
Маршруты API: GET /forecast, GET /health
"""

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.exceptions import (
    CityNotFoundError,
    InsufficientDataError,
    ModelNotAvailableError,
)
from app.core.logging import get_logger
from app.ml.model_registry import ModelRegistry, get_model_registry
from app.schemas.forecast import ErrorResponse, ForecastResponse, HealthResponse
from app.services.forecast_service import ForecastService
from app.services.geo_service import GeoService, get_geo_service

logger = get_logger(__name__)

router = APIRouter()


# ── Фабрики зависимостей ─────────────────────────────────────────────────────

def get_forecast_service(
    geo: Annotated[GeoService, Depends(get_geo_service)],
    registry: Annotated[ModelRegistry, Depends(get_model_registry)],
) -> ForecastService:
    """Возвращает сервис прогнозирования с внедренными зависимостями."""
    return ForecastService(geo_service=geo, model_registry=registry)


# ── Эндпоинты ────────────────────────────────────────────────────────────────

@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="Получить прогноз температуры для города",
    responses={
        200: {"description": "Успешный прогноз", "model": ForecastResponse},
        400: {"description": "Неверный ввод", "model": ErrorResponse},
        404: {"description": "Город не найден", "model": ErrorResponse},
        503: {"description": "Модель недоступна", "model": ErrorResponse},
    },
)
def get_forecast(
    city: Annotated[
        str,
        Query(
            min_length=1,
            max_length=100,
            description="Название города (например 'Saint Petersburg')",
            example="Saint Petersburg",
        ),
    ],
    forecast_date: Annotated[
        Optional[date],
        Query(
            alias="date",
            description="Целевая дата (ГГГГ-ММ-ДД). По умолчанию — завтрашний день.",
            example="2026-04-27",
        ),
    ] = None,
    service: ForecastService = Depends(get_forecast_service),
) -> ForecastResponse:
    """
    Возвращает прогнозируемую среднюю температуру (°C) для указанного города.

    - **city**: строка с названием города (геокодирование через Nominatim)
    - **date**: опциональная дата прогноза; по умолчанию — завтра

    Ошибки возвращаются в виде структурированного JSON с полями `error`, `detail`, `code`.
    """
    city = city.strip()
    if not city:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "Ошибка валидации", "detail": "название города не может быть пустым", "code": "INVALID_INPUT"},
        )

    try:
        return service.get_forecast(city=city, forecast_date=forecast_date)

    except CityNotFoundError as exc:
        logger.warning("city_not_found", city=exc.city)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "Город не найден", "detail": str(exc), "code": "CITY_NOT_FOUND"},
        )

    except ModelNotAvailableError as exc:
        logger.error("model_unavailable", reason=exc.reason)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"error": "Модель недоступна", "detail": str(exc), "code": "MODEL_UNAVAILABLE"},
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
                "error": "Недостаточно исторических данных",
                "detail": str(exc),
                "code": "INSUFFICIENT_DATA",
            },
        )

    except Exception as exc:  # pragma: no cover
        logger.exception("unexpected_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Внутренняя ошибка сервера", "detail": "Произошла непредвиденная ошибка", "code": "INTERNAL_ERROR"},
        )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Проверка работоспособности",
)
def health_check(
    registry: Annotated[ModelRegistry, Depends(get_model_registry)],
) -> HealthResponse:
    """Возвращает статус работоспособности приложения и состояние модели."""
    return HealthResponse(
        status="ok",
        model_loaded=registry.is_ready,
        model_version=registry.current_version,
    )
