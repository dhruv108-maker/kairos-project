from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPOSITORY_ROOT / ".env.local"


class Settings(BaseSettings):
    # Actual process environment variables take precedence over .env.local.
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    APP_NAME: str = "Kairos API"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

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

    # Backend-only Verifico OCR credentials. Lowercase verifico_api maps to
    # VERIFICO_API because settings are case-insensitive. Never use VITE_.
    VERIFICO_BASE_URL: str = "https://api.theverifico.com"
    VERIFICO_API: SecretStr | None = None

    JWT_SECRET_KEY: SecretStr
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
