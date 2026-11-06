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


def client_ip(request: Request) -> str:
    # За nginx реальный адрес приходит в X-Forwarded-For; uvicorn подставляет его в request.client,
    # если адрес прокси указан в --forwarded-allow-ips (см. Dockerfile и FORWARDED_ALLOW_IPS)
    return request.client.host if request.client else "unknown"


class SlidingWindow:
    """Счётчик событий по ключу за скользящее окно, в памяти процесса. Для нескольких инстансов — Redis."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit, self.window = limit, window_seconds
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self._calls = 0

    def _trim(self, key: str, now: float) -> deque[float]:
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        return q

    def _sweep(self, now: float) -> None:
        # Раз в тысячу обращений выбрасываем ключи без свежих событий, чтобы словарь не рос бесконечно
        self._calls += 1
        if self._calls % 1000:
            return
        for key in list(self.hits):
            if not self._trim(key, now):
                del self.hits[key]

    def full(self, key: str) -> bool:
        now = time.monotonic()
        self._sweep(now)
        full = len(self._trim(key, now)) >= self.limit
        if not self.hits[key]:
            del self.hits[key]
        return full

    def add(self, key: str) -> None:
        self.hits[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        self.hits.pop(key, None)


class RateLimiter(SlidingWindow):
    """Лимит публичных заявок, записей и заказов с одного IP."""

    def __init__(self) -> None:
        super().__init__(settings.rate_limit, settings.rate_window_seconds)

    def __call__(self, request: Request) -> None:
        ip = client_ip(request)
        if self.full(ip):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много заявок, попробуйте позже")
        self.add(ip)


rate_limit = RateLimiter()
# Неудачные входы считаем по паре «IP + e-mail»: перебор пароля упирается в 429
login_limit = SlidingWindow(settings.login_attempts, settings.login_window_seconds)
