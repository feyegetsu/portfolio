"""Настройки из переменных окружения. Значения по умолчанию подходят для локальной разработки."""

import os
from dataclasses import dataclass, field


def _list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    token_ttl_minutes: int = int(os.getenv("TOKEN_TTL_MINUTES", "720"))
    cors_origins: list[str] = field(
        default_factory=lambda: _list(os.getenv("CORS_ORIGINS", "https://feyegetsu.github.io,http://localhost:8000"))
    )
    # Сколько публичных заявок разрешено с одного IP за окно
    rate_limit: int = int(os.getenv("RATE_LIMIT", "20"))
    rate_window_seconds: int = int(os.getenv("RATE_WINDOW_SECONDS", "600"))
    # Первый владелец создаётся при старте, если пользователей ещё нет
    owner_email: str = os.getenv("OWNER_EMAIL", "owner@example.com")
    owner_password: str = os.getenv("OWNER_PASSWORD", "change-me-please")


settings = Settings()
