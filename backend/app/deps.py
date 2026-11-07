"""Общие зависимости роутов: сессия БД, текущий пользователь, проверка роли и доступа к сайту."""

import logging
import time
import uuid
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import User
from .security import decode_token
from .sites import SITES, Site

DB = Annotated[Session, Depends(get_db)]
_bearer = HTTPBearer(auto_error=False)

ROLE_LEVEL = {"staff": 1, "admin": 2, "owner": 3}
log = logging.getLogger("portfolio.api")


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
    """Счётчик событий по ключу за скользящее окно.

    Где хранятся события, решает store: в памяти процесса (по умолчанию) или в Redis (REDIS_URL),
    чтобы лимит был общим для всех копий API за балансировщиком.
    """

    def __init__(self, name: str, limit: int, window_seconds: int, store: "Store | None" = None) -> None:
        self.name, self.limit, self.window = name, limit, window_seconds
        self.store = store or make_store()

    def full(self, key: str) -> bool:
        return self.store.count(self.name, key, self.window) >= self.limit

    def add(self, key: str) -> None:
        self.store.add(self.name, key, self.window)

    def reset(self, key: str) -> None:
        self.store.reset(self.name, key)

    def clear(self) -> None:
        self.store.clear(self.name)


class MemoryStore:
    """События в словаре процесса. Подходит для одной копии API и для тестов."""

    def __init__(self) -> None:
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self._calls = 0

    def _trim(self, k: str, now: float, window: int) -> deque[float]:
        q = self.hits[k]
        while q and now - q[0] > window:
            q.popleft()
        return q

    def count(self, name: str, key: str, window: int) -> int:
        now, k = time.monotonic(), f"{name}:{key}"
        self._calls += 1
        if not self._calls % 1000:
            # Раз в тысячу обращений выбрасываем ключи без свежих событий, чтобы словарь не рос бесконечно
            for old in list(self.hits):
                if not self._trim(old, now, window):
                    del self.hits[old]
        n = len(self._trim(k, now, window))
        if not n:
            self.hits.pop(k, None)
        return n

    def add(self, name: str, key: str, window: int) -> None:
        self.hits[f"{name}:{key}"].append(time.monotonic())

    def reset(self, name: str, key: str) -> None:
        self.hits.pop(f"{name}:{key}", None)

    def clear(self, name: str) -> None:
        for k in [k for k in self.hits if k.startswith(f"{name}:")]:
            del self.hits[k]


class RedisStore:
    """События в Redis: отсортированное множество на ключ, оценка — время события.

    Если Redis недоступен, лимит не применяется, а в лог пишется предупреждение:
    лучше пропустить лишнюю заявку, чем перестать принимать заказы.
    """

    PREFIX = "pf:limit:"

    def __init__(self, client) -> None:
        self.r = client

    def _k(self, name: str, key: str) -> str:
        return f"{self.PREFIX}{name}:{key}"

    def count(self, name: str, key: str, window: int) -> int:
        k, now = self._k(name, key), time.time()
        try:
            pipe = self.r.pipeline()
            pipe.zremrangebyscore(k, 0, now - window)
            pipe.zcard(k)
            return pipe.execute()[1]
        except RedisError as e:
            log.warning("Redis недоступен, лимит %s не проверен: %s", name, e)
            return 0

    def add(self, name: str, key: str, window: int) -> None:
        k, now = self._k(name, key), time.time()
        try:
            pipe = self.r.pipeline()
            pipe.zadd(k, {uuid.uuid4().hex: now})
            pipe.expire(k, window)
            pipe.execute()
        except RedisError as e:
            log.warning("Redis недоступен, событие %s не записано: %s", name, e)

    def reset(self, name: str, key: str) -> None:
        try:
            self.r.delete(self._k(name, key))
        except RedisError as e:
            log.warning("Redis недоступен: %s", e)

    def clear(self, name: str) -> None:
        for k in self.r.scan_iter(f"{self.PREFIX}{name}:*"):
            self.r.delete(k)


Store = MemoryStore | RedisStore
_redis_store: RedisStore | None = None


def make_store() -> Store:
    """Redis, если задан REDIS_URL, иначе память процесса. Одно подключение на все лимиты."""
    global _redis_store
    if not settings.redis_url:
        return MemoryStore()
    if _redis_store is None:
        import redis

        _redis_store = RedisStore(redis.Redis.from_url(settings.redis_url, socket_timeout=0.5, socket_connect_timeout=0.5))
    return _redis_store


class RateLimiter(SlidingWindow):
    """Лимит публичных заявок, записей и заказов с одного IP."""

    def __init__(self) -> None:
        super().__init__("public", settings.rate_limit, settings.rate_window_seconds)

    def __call__(self, request: Request) -> None:
        ip = client_ip(request)
        if self.full(ip):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много заявок, попробуйте позже")
        self.add(ip)


rate_limit = RateLimiter()
# Неудачные входы считаем по паре «IP + e-mail»: перебор пароля упирается в 429
login_limit = SlidingWindow("login", settings.login_attempts, settings.login_window_seconds)
