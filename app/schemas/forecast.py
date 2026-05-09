from datetime import date
from typing import Optional, Any

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
    time: date
    city: str
    country_code: str = "ru"
    params: list[str]
    coords: str
    payload: dict[str, Any]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: str
