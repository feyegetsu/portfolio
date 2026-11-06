"""Настройки из переменных окружения.

В продакшене SECRET_KEY и OWNER_PASSWORD обязательны: без них API не стартует (см. check_secrets).
Для локальной разработки можно запустить с ENV=development, тогда подойдут значения по умолчанию.
"""

import os
from dataclasses import dataclass, field

DEV_SECRET = "dev-secret-change-me"
DEV_PASSWORD = "change-me-please"


def _list(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    env: str = os.getenv("ENV", "production")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")
    secret_key: str = os.getenv("SECRET_KEY", DEV_SECRET)
    token_ttl_minutes: int = int(os.getenv("TOKEN_TTL_MINUTES", "720"))
    cors_origins: list[str] = field(
        default_factory=lambda: _list(os.getenv("CORS_ORIGINS", "https://feyegetsu.github.io,http://localhost:8000"))
    )
    # Сколько публичных заявок разрешено с одного IP за окно
    rate_limit: int = int(os.getenv("RATE_LIMIT", "20"))
    rate_window_seconds: int = int(os.getenv("RATE_WINDOW_SECONDS", "600"))
    # Попытки входа: после стольких ошибок e-mail с этого IP блокируется на окно
    login_attempts: int = int(os.getenv("LOGIN_ATTEMPTS", "5"))
    login_window_seconds: int = int(os.getenv("LOGIN_WINDOW_SECONDS", "900"))
    # Максимальный размер тела запроса: формы и заказы укладываются с огромным запасом
    max_body_bytes: int = int(os.getenv("MAX_BODY_BYTES", "65536"))
    # Первый владелец создаётся при старте, если пользователей ещё нет
    owner_email: str = os.getenv("OWNER_EMAIL", "owner@example.com")
    owner_password: str = os.getenv("OWNER_PASSWORD", DEV_PASSWORD)


def check_secrets(s: "Settings") -> None:
    """Не даём API стартовать с ключом и паролем, которые лежат в открытом репозитории."""
    if s.env == "development":
        return
    problems = []
    if s.secret_key == DEV_SECRET or len(s.secret_key) < 32 or "замените" in s.secret_key:
        problems.append("SECRET_KEY: задайте случайную строку длиной от 32 символов (python -c \"import secrets; print(secrets.token_urlsafe(48))\")")
    if s.owner_password == DEV_PASSWORD or len(s.owner_password) < 10 or "замените" in s.owner_password:
        problems.append("OWNER_PASSWORD: задайте свой пароль владельца длиной от 10 символов")
    if problems:
        raise RuntimeError("API не запущен, небезопасные настройки:\n- " + "\n- ".join(problems)
                           + "\nДля локальной разработки запустите с ENV=development.")


settings = Settings()
