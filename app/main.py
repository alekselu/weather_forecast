from fastapi import FastAPI
from app.db import get_connection
import os

app = FastAPI()


@app.get("/")
def root():
    return {"message": "API работает"}


@app.get("/health/db")
def check_db():
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()
        conn.close()
        return {
            "status": "ok",
            "db_response": result[0]
        }
    except Exception as e:
        return {
            "status": "error",
            "details": str(e),
            "db_host": os.getenv("DB_HOST", "db"),
            "dbname": os.getenv("DB_NAME", "weather"),
            "user": os.getenv("DB_USER", "weather_user"),
            "password": os.getenv("DB_PASSWORD", "weather_pass"),
        }