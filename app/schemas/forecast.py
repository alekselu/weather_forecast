from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Схемы запросов ──────────────────────────────────────────────────────────

class ForecastRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=100, examples=["Saint Petersburg"])
    date: Optional[date] = Field(
        default=None,
        description="Дата прогноза (ГГГГ-ММ-ДД). По умолчанию — завтрашний день.",
        examples=["2026-04-27"],
    )

    @field_validator("city")
    @classmethod
    def city_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("название города не может быть пустым")
        return stripped


# ── Схемы ответов ────────────────────────────────────────────────────────────

class ForecastResponse(BaseModel):
    city: str
    date: date
    avg_temperature_c: float = Field(
        ...,
        description="Прогнозируемая средняя температура в °C",
        examples=[8.3],
    )
    model_version: str = Field(
        default="stub-v0",
        description="Идентификатор модели, которая сгенерировала этот прогноз",
    )
    confidence: Optional[str] = Field(
        default=None,
        description="Опциональное качественное описание уверенности: low | medium | high",
    )

    model_config = {"json_schema_extra": {
        "example": {
            "city": "Saint Petersburg",
            "date": "2026-04-27",
            "avg_temperature_c": 8.3,
            "model_version": "stub-v0",
            "confidence": None,
        }
    }}


class HealthResponse(BaseModel):
    """Ответ на проверку работоспособности сервиса."""
    status: str
    model_loaded: bool
    model_version: str


class ErrorResponse(BaseModel):
    """Структурированный ответ с ошибкой."""
    error: str
    detail: str
    code: str
