from fastapi import FastAPI
from typing import Any
from app import db

app = FastAPI()


@app.get("/")
def root():
    return {"message": "API работает"}


@app.get("/health/db")
def check_db() -> dict[str, Any]:
    result: db.DatabaseHealthResponse = db.check_db()
    return result.to_dict()
