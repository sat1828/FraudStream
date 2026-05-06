"""Application configuration using Pydantic v2 Settings."""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # App
    APP_NAME: str = "UPI Fraud Detection API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "upi_fraud"
    POSTGRES_USER: str = "upi_user"
    POSTGRES_PASSWORD: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    RATE_LIMIT_REQUESTS: int = 1000
    RATE_LIMIT_WINDOW: int = 60
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 5
    LOGIN_RATE_LIMIT_WINDOW: int = 900

    # Kafka/Redpanda
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_TRANSACTIONS: str = "upi-raw-transactions"
    KAFKA_TOPIC_PREDICTIONS: str = "upi-predictions"

    # MLflow
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"
    MLFLOW_EXPERIMENT_NAME: str = "upi-fraud-detection"
    MLFLOW_MODEL_NAME: str = "upi-fraud-xgboost"

    # Feast
    FEAST_REPO_PATH: str = "/mlops/feast_repo/feature_repo"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://frontend:3000",
    ]

    # ML Model
    MODEL_FRAUD_THRESHOLD: float = 0.5
    MODEL_REVIEW_THRESHOLD: float = 0.3
    DRIFT_DETECTION_WINDOW: int = 500
    DRIFT_THRESHOLD: float = 0.1

    # MLOps
    BACKEND_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    GRAFANA_URL: str = "http://localhost:3001"

    # Security
    SECRET_KEY: str
    ADMIN_EMAIL: str = "admin@upi.ai"
    ADMIN_PASSWORD: str = "password"
    MAX_WS_CONNECTIONS: int = 100
    OPENAPI_ENABLED: bool = True

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_set(cls, v: str) -> str:
        if not v or v.startswith("CHANGE_ME"):
            raise ValueError(
                "SECRET_KEY must be set to a secure random value. "
                "Generate one with: openssl rand -hex 32"
            )
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("POSTGRES_PASSWORD")
    @classmethod
    def postgres_password_must_be_set(cls, v: str) -> str:
        if not v or v.startswith("CHANGE_ME"):
            raise ValueError(
                "POSTGRES_PASSWORD must be set to a strong random password"
            )
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
