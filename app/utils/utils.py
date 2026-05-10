import os
from dotenv import load_dotenv


def _get_db_url() -> str:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    load_dotenv(os.path.join(BASE_DIR, ".env"))

    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL is None:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    return DATABASE_URL


DATABASE_URL: str = _get_db_url()
