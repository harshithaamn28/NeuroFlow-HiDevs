from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL
    postgres_url: str

    # Redis
    redis_url: str

    # MLflow
    mlflow_url: str = "http://mlflow:5000"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )