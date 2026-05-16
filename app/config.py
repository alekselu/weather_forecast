from dotenv import load_dotenv
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    MODEL_PATH: str = "/models"
    RETRAIN_HOUR: int = 2
    RETRAIN_MINUTE: int = 0
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    class Config:
        env_file = ".env"


settings = Settings()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
load_dotenv(os.path.join(BASE_DIR, ".env"))

ML_SERVICE_URL = os.getenv("ML_SERVICE_URL")
