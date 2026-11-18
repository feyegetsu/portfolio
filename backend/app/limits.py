"""Лимиты частоты: заявки и чтения с одного IP, попытки входа. Счётчики в памяти процесса или в Redis."""

import functools
import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status
from redis.exceptions import RedisError

from .config import settings
from .deps import client_ip

log = logging.getLogger("portfolio.api")


class SlidingWindow:
    """Счётчик событий по ключу за скользящее окно.

    Где хранятся события, решает store: в памяти процесса (по умолчанию) или в Redis (REDIS_URL),
    чтобы лимит был общим для всех копий API за балансировщиком.
    """

    def __init__(self, name: str, limit: int, window_seconds: int, store: "Store | None" = None, fail_open: bool = True) -> None:
        self.name, self.limit, self.window = name, limit, window_seconds
        self.store = store or make_store()
        # Что делать, если счётчик недоступен (Redis упал): пропустить (заявки) или закрыть (вход)
        self.fail_open = fail_open

    def full(self, key: str) -> bool:
        n = self.store.count(self.name, key, self.window)
        if n is None:
            if self.fail_open:
                return False
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Вход временно недоступен, попробуйте через минуту")
        return n >= self.limit

    @property
    def wait_minutes(self) -> int:
        return max(1, -(-self.window // 60))

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

    Если Redis недоступен, count возвращает None, а в лог пишется предупреждение. Лимит заявок тогда
    не применяется (лучше пропустить лишнюю заявку, чем перестать принимать заказы), а вход закрывается:
    без счётчика перебор пароля ничем не ограничен.
    """

    PREFIX = "pf:limit:"

    def __init__(self, client) -> None:
        self.r = client

    def _k(self, name: str, key: str) -> str:
        return f"{self.PREFIX}{name}:{key}"

    def count(self, name: str, key: str, window: int) -> int | None:
        k, now = self._k(name, key), time.time()
        try:
            pipe = self.r.pipeline()
            pipe.zremrangebyscore(k, 0, now - window)
            pipe.zcard(k)
            return pipe.execute()[1]
        except RedisError as e:
            log.warning("Redis недоступен, лимит %s не проверен: %s", name, e)
            return None

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
        try:
            for k in self.r.scan_iter(f"{self.PREFIX}{name}:*"):
                self.r.delete(k)
        except RedisError as e:
            log.warning("Redis недоступен, лимит %s не очищен: %s", name, e)


Store = MemoryStore | RedisStore


@functools.cache
def _redis_store(url: str) -> RedisStore:
    """Одно подключение к Redis на все лимиты процесса."""
    import redis

    return RedisStore(redis.Redis.from_url(url, socket_timeout=0.5, socket_connect_timeout=0.5))


def make_store() -> Store:
    """Redis, если задан REDIS_URL, иначе память процесса."""
    return _redis_store(settings.redis_url) if settings.redis_url else MemoryStore()


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


class ReadLimiter(SlidingWindow):
    """Лимит публичных чтений с одного IP: дешёвая нагрузка на базу. Без Redis не применяется."""

    def __init__(self) -> None:
        super().__init__("read", settings.read_limit, 60)

    def __call__(self, request: Request) -> None:
        ip = client_ip(request)
        if self.full(ip):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Слишком много запросов, подождите минуту")
        self.add(ip)


read_limit = ReadLimiter()
# Неудачные входы: по паре «IP + e-mail» (обычная опечатка), по аккаунту со всех IP (распределённый перебор)
# и по IP на любые e-mail (перебор адресов). Без счётчика вход закрывается — fail_open=False
login_limit = SlidingWindow("login", settings.login_attempts, settings.login_window_seconds, fail_open=False)
login_account_limit = SlidingWindow("login-acc", settings.login_account_attempts, settings.login_account_window_seconds, fail_open=False)
login_ip_limit = SlidingWindow("login-ip", settings.login_ip_attempts, settings.login_ip_window_seconds, fail_open=False)
LOGIN_LIMITS = (login_limit, login_account_limit, login_ip_limit)


def login_keys(request: Request, email: str) -> tuple[str, str, str]:
    """Ключи для трёх лимитов входа в том же порядке, что LOGIN_LIMITS."""
    ip = client_ip(request)
    return f"{ip}|{email}", email, ip


def check_login_allowed(keys: tuple[str, str, str]) -> None:
    for limiter, key in zip(LOGIN_LIMITS, keys, strict=True):
        if limiter.full(key):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                f"Слишком много попыток входа, подождите {limiter.wait_minutes} мин.")


def login_failed(keys: tuple[str, str, str]) -> None:
    for limiter, key in zip(LOGIN_LIMITS, keys, strict=True):
        limiter.add(key)
