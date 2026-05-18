from datetime import date
from typing import Optional, Any

from pydantic import BaseModel, Field, field_validator, model_validator

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


class ForecastPayload(BaseModel):
    """Class containing results for all parameters requested in each category."""

    hourly: dict[str, list] = {}
    daily: dict[str, list] = {}


class ForecastResponse(BaseModel):
    start_date: date
    end_date: date
    city: str
    params: list[str]
    coords: str
    payload: ForecastPayload


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_version: str


class ErrorResponse(BaseModel):
    error: str
    detail: str
    code: str


class PredictRequest(BaseModel):
    latitude: float
    longitude: float
    start_date: date
    end_date: date
    hourly: list[str] = []
    daily: list[str] = []

    @model_validator(mode="after")
    def check_dates(self) -> "PredictRequest":
        if self.start_date > self.end_date:
            raise ValueError("start_date must be ≤ end_date")
        if not self.hourly and not self.daily:
            raise ValueError("At least one of hourly or daily params must be provided")
        return self


class PredictResponse(BaseModel):
    hourly: dict[str, list] = {}
    daily: dict[str, list] = {}


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded" | "no_model"
    model_loaded: bool
    model_version: str
    retraining_now: bool


class RetrainResponse(BaseModel):
    status: str  # "started" | "already_running"
    message: str
