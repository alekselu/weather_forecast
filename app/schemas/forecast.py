from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Request schemas ──────────────────────────────────────────────────────────


class ForecastRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=100, examples=["Saint Petersburg"])
    date_: Optional[date] = Field(
        default=None,
        description="Forecast date (YYYY-MM-DD). Defaults to tomorrow.",
        examples=["2026-04-27"],
    )

    @field_validator("city")
    @classmethod
    def city_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("city must not be blank")
        return stripped


# ── Response schemas ─────────────────────────────────────────────────────────


class ForecastResponse(BaseModel):
    city: str
    date: date
    avg_temperature_c: float = Field(
        ...,
        description="Predicted average temperature in °C",
        examples=[8.3],
    )
    model_version: str = Field(
        default="stub-v0",
        description="Identifier of the model that produced this forecast",
    )
    confidence: Optional[str] = Field(
        default=None,
        description="Optional qualitative confidence: low | medium | high",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "city": "Saint Petersburg",
                "date": "2026-04-27",
                "avg_temperature_c": 8.3,
                "model_version": "stub-v0",
                "confidence": None,
            }
        }
    }


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: str
