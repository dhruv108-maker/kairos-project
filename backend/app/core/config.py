from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# Repository root: kairos-project/
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPOSITORY_ROOT / ".env.local"


class Settings(BaseSettings):
    # Always load environment settings from the repository-root .env.local.
    # Actual process environment variables take precedence over file values.
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "Kairos API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database connection settings are read independently from the environment.
    DB_HOST: str
    DB_PORT: int = 3306
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_NAME: str = "kairos"

    SQL_ECHO: bool = False
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    VPS_STORAGE_PATH: Path = Path("./var/kairos/storage")
    FRONTEND_URL: str = "http://localhost:5173"

    RESEND_API_KEY: SecretStr | None = None
    RESEND_FROM_EMAIL: str | None = None
    MAIL_FROM_NAME: str = "Kairos"

    # Signzy Aadhaar verification. Keep credentials in deployment secrets/.env.local,
    # never in source control or frontend variables. Use preproduction until enabled.
    SIGNZY_BASE_URL: str = "https://api-preproduction.signzy.app"
    SIGNZY_USERNAME: SecretStr | None = None
    SIGNZY_PASSWORD: SecretStr | None = None
    SIGNZY_AADHAAR_ENABLED: bool = False

    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
