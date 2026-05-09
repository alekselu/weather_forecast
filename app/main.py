from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Annotated, Dict
from app import db
from datetime import date
from app.core.logging import setup_logging
from app.utils.geolocation import GeoCoder, City, Coordinates

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


@app.get("/")
def root():
    return {"message": "API работает"}


@app.get("/health/db")
def check_db() -> dict[str, Any]:
    result: db.DatabaseHealthResponse = db.check_db()
    return result.to_dict()


# Example: GET /forecast?time=2026-05-06&params=temperature&params=humidity&params=wind
@app.get("/forecast")
async def get_forecast(
    time: Annotated[date, Query()],
    city: Annotated[str, Query()],
    country_code: str = "ru",
    params: list[str] = Query(),
) -> dict[str, Any]:
    result: Dict[str, Any] = {}
    result["time"] = time
    result["city"] = city
    try:
        coords: Coordinates = await geocoder.fetch_location_from(
            City(city, country_code)
        )
        result["coords"] = str(coords)
    except Exception as e:
        result["coords"] = str(e)
    result["country_code"] = country_code
    result["params"] = params
    return result
