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


def build_forecast_url(
    city: str = "Saint Petersburg",
    start_date: str | None = None,
    end_date: str | None = None,
    time: str | None = None,
    params: list[str] | None = None,
    country_code: str = "ru",
) -> str:
    """Build request string for GET /forecast."""
    parts = [f"city={city}", f"country_code={country_code}"]
    if start_date:
        parts.append(f"start_date={start_date}")
    if end_date:
        parts.append(f"end_date={end_date}")
    if time:
        parts.append(f"time={time}")
    for p in params or []:
        parts.append(f"params={p}")
    return "/forecast?" + "&".join(parts)
