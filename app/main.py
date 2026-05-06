from fastapi import FastAPI, Query
from typing import Any, Annotated, Dict
from app import db
from datetime import date
from app.core.logging import setup_logging

setup_logging()
import logging

logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/")
def root():
    return {"message": "API работает"}


@app.get("/health/db")
def check_db() -> dict[str, Any]:
    result: db.DatabaseHealthResponse = db.check_db()
    return result.to_dict()


# Example: GET /forecast?time=2026-05-06&params=temperature&params=humidity&params=wind
@app.get("/forecast")
def get_forecast(
    time: Annotated[date, Query()], params: list[str] = Query()
) -> dict[str, Any]:
    result: Dict[str, Any] = {}
    result["time"] = time
    result["params"] = params
    return result
