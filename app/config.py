from dotenv import load_dotenv
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    MODEL_PATH: str = "/models"
    RETRAIN_HOUR: int = 2
    RETRAIN_MINUTE: int = 0
    DB_HOST: str = Field(validation_alias="POSTGRES_HOST")
    DB_PORT: int = Field(5432, validation_alias="POSTGRES_PORT")
    DB_NAME: str = Field(validation_alias="POSTGRES_DB")
    DB_USER: str = Field(validation_alias="POSTGRES_USER")
    DB_PASSWORD: str = Field(validation_alias="POSTGRES_PASSWORD")

    ML_SERVICE_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()

# BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
# load_dotenv(os.path.join(BASE_DIR, ".env"))

# ML_SERVICE_URL = os.getenv("ML_SERVICE_URL")
