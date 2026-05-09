import os
from dotenv import load_dotenv


def _get_db_url() -> str:
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    load_dotenv(os.path.join(BASE_DIR, ".env"))

    OPRIONAL_DATABASE_URL = os.getenv("DATABASE_URL")
    if OPRIONAL_DATABASE_URL is None:
        raise RuntimeError("DATABASE_URL environment variable is not set.")
    DATABASE_URL: str = OPRIONAL_DATABASE_URL
    return DATABASE_URL


DATABASE_URL: str = _get_db_url()


import logging


class LoggerAdapter(logging.LoggerAdapter):
    def __init__(self, prefix: str, logger, extra=None):
        super().__init__(logger, extra)
        self.prefix = prefix

    def process(self, msg, kwargs):
        return f"[{self.prefix}] {msg}", kwargs
