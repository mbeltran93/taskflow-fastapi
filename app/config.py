"""Application settings, loaded from environment variables (see .env.example)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "TaskFlow API"
    environment: str = "development"

    # Database
    database_url: str = (
        "postgresql+psycopg://taskflow:taskflow@localhost:5432/taskflow"
    )

    # Auth
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h, convenient for a portfolio demo


@lru_cache
def get_settings() -> Settings:
    return Settings()
