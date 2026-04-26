"""
Фабрика приложения.

- Регистрирует lifespan для запуска/останова (загрузка модели, пул соединений с БД и т.д.)
- Подключает все роутеры
- Устанавливает глобальные обработчики исключений для чистых JSON-ответов с ошибками
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.exceptions import WeatherForecastError
from app.core.logging import get_logger, setup_logging
from app.ml.model_registry import ModelStub, get_model_registry

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Жизненный цикл приложения: запуск → yield → останов."""
    setup_logging()
    settings = get_settings()

    logger.info("app_starting", env=settings.app_env)

    # Загружаем модель — заглушка для v0; в v1 заменить на реальный загрузчик артефактов
    registry = get_model_registry()
    registry.load(ModelStub())

    logger.info("app_ready", host=settings.app_host, port=settings.app_port)
    yield

    logger.info("app_shutting_down")


def create_app() -> FastAPI:
    """Создаёт и настраивает экземпляр FastAPI приложения."""
    settings = get_settings()

    app = FastAPI(
        title="Weather Forecast API",
        description=(
            "Предсказывает среднюю температуру на завтра (или любую указанную дату) "
            "для заданного города с использованием модели машинного обучения."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        debug=settings.app_env == "development",
    )

    # ── Роутеры ──────────────────────────────────────────────────────────────
    app.include_router(router, prefix="/api/v1", tags=["forecast"])

    # Корневые алиасы для удобства (без префикса) для обратной совместимости
    app.include_router(router, tags=["forecast (root)"], include_in_schema=False)

    # ── Глобальные обработчики исключений ─────────────────────────────────────

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Возвращает структурированный JSON при ошибках валидации Pydantic / FastAPI."""
        details = exc.errors()
        logger.warning("request_validation_error", errors=details, path=str(request.url))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "Ошибка валидации",
                "detail": details,
                "code": "VALIDATION_ERROR",
            },
        )

    @app.exception_handler(WeatherForecastError)
    async def domain_exception_handler(
        request: Request, exc: WeatherForecastError
    ) -> JSONResponse:
        """Перехватывает необработанные доменные исключения, которые не были пойманы в роутере."""
        logger.error("unhandled_domain_error", error=str(exc), path=str(request.url))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Ошибка приложения",
                "detail": str(exc),
                "code": "APPLICATION_ERROR",
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Последний обработчик — предотвращает утечку стектрейсов 500 к клиентам."""
        logger.exception("unhandled_exception", error=str(exc), path=str(request.url))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Внутренняя ошибка сервера",
                "detail": "Произошла непредвиденная ошибка.",
                "code": "INTERNAL_ERROR",
            },
        )

    return app


# Для `uvicorn app.main:app`
app = create_app()
