"""Лимиты в Redis: общий счётчик для нескольких копий API и работа при недоступном Redis."""

import fakeredis
import pytest

from app.config import database_url
from app.deps import MemoryStore, RedisStore, SlidingWindow


@pytest.fixture
def server():
    return fakeredis.FakeServer()


def test_redis_limit_is_shared_between_api_copies(server):
    # Две копии API за балансировщиком: у каждой своё подключение, но Redis один
    first = SlidingWindow("public", 3, 60, RedisStore(fakeredis.FakeRedis(server=server)))
    second = SlidingWindow("public", 3, 60, RedisStore(fakeredis.FakeRedis(server=server)))
    for _ in range(2):
        first.add("1.2.3.4")
    second.add("1.2.3.4")
    assert first.full("1.2.3.4") and second.full("1.2.3.4")
    assert not first.full("5.6.7.8")


def test_redis_reset_and_separate_limits(server):
    store = RedisStore(fakeredis.FakeRedis(server=server))
    login = SlidingWindow("login", 2, 60, store)
    public = SlidingWindow("public", 2, 60, store)
    login.add("ip|a@b.ru")
    login.add("ip|a@b.ru")
    assert login.full("ip|a@b.ru")
    assert not public.full("ip|a@b.ru")  # у разных лимитов свои счётчики
    login.reset("ip|a@b.ru")
    assert not login.full("ip|a@b.ru")


def test_redis_keys_expire_with_window(server):
    client = fakeredis.FakeRedis(server=server)
    SlidingWindow("public", 3, 60, RedisStore(client)).add("1.2.3.4")
    ttl = client.ttl("pf:limit:public:1.2.3.4")
    assert 0 < ttl <= 60  # ключ не живёт вечно


def test_redis_down_does_not_block_orders(server, caplog):
    server.connected = False
    limit = SlidingWindow("public", 1, 60, RedisStore(fakeredis.FakeRedis(server=server)))
    limit.add("1.2.3.4")
    limit.add("1.2.3.4")
    assert not limit.full("1.2.3.4")
    assert "Redis недоступен" in caplog.text


def test_memory_store_still_works():
    limit = SlidingWindow("public", 2, 60, MemoryStore())
    limit.add("x")
    assert not limit.full("x")
    limit.add("x")
    assert limit.full("x")
    limit.clear()
    assert not limit.full("x")


@pytest.mark.parametrize("given, expected", [
    ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
    ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
    ("sqlite:///./portfolio.db", "sqlite:///./portfolio.db"),
])
def test_database_url_from_hosting(given, expected):
    assert database_url(given) == expected


def test_health_reports_db_and_limits(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "db": "ok", "limits": "memory"}
