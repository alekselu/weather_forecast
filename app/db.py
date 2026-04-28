import os
import psycopg
from typing import Any


def connection():
    return psycopg.connect(**connection_params())


def connection_params() -> dict[str, Any]:
    return {
        "host": os.getenv("DB_HOST", "db"),
        "port": os.getenv("DB_PORT", 5432),
        "dbname": os.getenv("DB_NAME", "weather"),
        "user": os.getenv("DB_USER", "admin"),
        "password": os.getenv("DB_PASSWORD"),
    }
