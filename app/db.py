import os
import psycopg

def get_connection():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", 5432),
        dbname=os.getenv("DB_NAME", "weather"),
        user=os.getenv("DB_USER", "admin"),
        password=os.getenv("DB_PASSWORD", "weather_pass"),
    )