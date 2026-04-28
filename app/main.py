from fastapi import FastAPI
from typing import Any
from app.db import connection, connection_params

app = FastAPI()


@app.get("/")
def root():
    return {"message": "API работает"}


@app.get("/health/db")
def check_db() -> dict[str, Any]:
    try:
        conn = connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            result = cur.fetchone()
        conn.close()
        return {"status": "ok", "db_response": result[0]}
    except Exception as e:
        return {
            "status": "error",
            "details": str(e),
            **connection_params(),
        }
