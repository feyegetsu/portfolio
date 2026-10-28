"""Общие зависимости роутов: сессия БД, текущий пользователь, проверка роли и доступа к сайту."""

import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User
from .security import decode_token
from .sites import SITES, Site

DB = Annotated[Session, Depends(get_db)]
_bearer = HTTPBearer(auto_error=False)

ROLE_LEVEL = {"staff": 1, "admin": 2, "owner": 3}


def get_site(site: str) -> Site:
    if site not in SITES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сайт не найден")
    return SITES[site]


def current_user(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]) -> User:
    user_id = decode_token(creds.credentials) if creds else None
    user = db.get(User, user_id) if user_id else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Нужно войти", headers={"WWW-Authenticate": "Bearer"})
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def require(role: str):
    """Зависимость «минимальная роль»: staff < admin < owner."""

    def check(user: CurrentUser) -> User:
        if ROLE_LEVEL[user.role] < ROLE_LEVEL[role]:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Недостаточно прав")
        return user

    return check


def allowed_sites(user: User) -> list[str]:
    return list(SITES) if user.sites is None else [s for s in user.sites if s in SITES]


def check_site_access(user: User, site: str) -> None:
    if site not in allowed_sites(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа к этому сайту")


class RateLimiter:
    """Простое ограничение частоты по IP в памяти процесса. Для нескольких инстансов заменяется на Redis."""

    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def __call__(self, request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self.hits[ip]
        while window and now - window[0] > settings.rate_window_seconds:
            window.popleft()
        if len(window) >= settings.rate_limit:
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много заявок, попробуйте позже")
        window.append(now)


rate_limit = RateLimiter()
