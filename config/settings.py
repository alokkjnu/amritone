"""
Application settings using Pydantic Settings.
Loads configuration from environment variables and .env file.
"""

from __future__ import annotations

import secrets
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central application configuration."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "Amrit One"
    APP_TAGLINE: str = "Pure. Natural. Authentic."
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    BASE_URL: str = "http://localhost:8000"
    SECRET_KEY: str = secrets.token_urlsafe(64)
    ALLOWED_HOSTS: list[str] = ["*"]

    # ── Database ─────────────────────────────────────────────────────────────
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_NAME: str = "amritone"
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "password"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # ── JWT ───────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = secrets.token_urlsafe(64)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 300  # seconds

    # ── Email ─────────────────────────────────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@amritone.com"
    SMTP_FROM_NAME: str = "Amrit One"
    SMTP_TLS: bool = True

    # ── Storage ───────────────────────────────────────────────────────────────
    UPLOAD_DIR: Path = BASE_DIR / "static" / "uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]

    # ── Security ─────────────────────────────────────────────────────────────
    CSRF_SECRET: str = secrets.token_urlsafe(32)
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    BCRYPT_ROUNDS: int = 12

    # ── Pagination ────────────────────────────────────────────────────────────
    DEFAULT_PAGE_SIZE: int = 12
    MAX_PAGE_SIZE: int = 100

    # ── Business ─────────────────────────────────────────────────────────────
    CURRENCY: str = "INR"
    CURRENCY_SYMBOL: str = "₹"
    GST_REGISTRATION: str = ""
    COMPANY_NAME: str = "Amrit One Organics Pvt. Ltd."
    COMPANY_ADDRESS: str = "India"
    COMPANY_PHONE: str = "+91-XXXXXXXXXX"
    COMPANY_EMAIL: str = "support@amritone.in"
    LOW_STOCK_THRESHOLD: int = 10

    # ── OTP ──────────────────────────────────────────────────────────────────
    OTP_EXPIRY_MINUTES: int = 10
    OTP_LENGTH: int = 6

    # ── Admin ─────────────────────────────────────────────────────────────────
    ADMIN_PATH: str = "/admin"
    SUPER_ADMIN_EMAIL: str = "admin@amritone.in"
    SUPER_ADMIN_PASSWORD: str = "Admin@123"

    @field_validator("UPLOAD_DIR", mode="before")
    @classmethod
    def create_upload_dir(cls, v: Any) -> Path:
        path = Path(v)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()


settings = get_settings()
