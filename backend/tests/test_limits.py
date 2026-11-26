"""Лимиты в Redis: общий счётчик для нескольких копий API и работа при недоступном Redis."""

import fakeredis
import pytest

from app.config import database_url
from app.limits import MemoryStore, RedisStore, SlidingWindow


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


def test_read_limit(client):
    # SEC-011: публичные GET тоже ограничены по IP, но опрос статуса заказа раз в 2 секунды проходит с запасом
    from app.limits import read_limit
    assert read_limit.limit >= 60
    codes = [client.get("/api/v1/sites/sushi/catalog").status_code for _ in range(read_limit.limit + 1)]
    assert codes[:-1] == [200] * read_limit.limit
    assert codes[-1] == 429
    assert client.get("/api/v1/sites").status_code == 429


def test_read_params_are_bounded(client):
    assert client.get("/api/v1/sites/barbershop/slots", params={"resource": "x" * 101, "date": "2026-01-01"}).status_code == 422
    assert client.get(f"/api/v1/sites/sushi/orders/{'x' * 33}").status_code == 422


def test_redis_clear_when_down(server, caplog):
    # BE-004: очистка лимита при недоступном Redis не роняет процесс, как и остальные операции
    server.connected = False
    SlidingWindow("public", 1, 60, RedisStore(fakeredis.FakeRedis(server=server))).clear()
    assert "не очищен" in caplog.text


def test_settings_read_at_instantiation(monkeypatch):
    from app.config import Settings, get_settings
    monkeypatch.setenv("RATE_LIMIT", "77")
    assert Settings().rate_limit == 77  # окружение читается при создании, а не при импорте модуля
    assert get_settings() is get_settings()


def test_health_when_database_is_down(client, monkeypatch):
    # TEST-002: хостинг перезапускает API по 503, если база недоступна
    from app import main

    class Broken:
        def __enter__(self):
            raise OSError("база недоступна")

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(main, "SessionLocal", lambda: Broken())
    r = client.get("/health")
    assert r.status_code == 503 and r.json()["db"] == "unavailable"


def test_rules_export_writes_only_on_change(tmp_path):
    from app import rules_export
    target = tmp_path / "api.js"
    target.write_text(f"// до\n  {rules_export.START} старое */\n  {rules_export.END}\n// после\n", encoding="utf-8")
    assert rules_export.write(target) is True
    assert rules_export.write(target) is False
    assert rules_export.render() in target.read_text(encoding="utf-8")


def test_memory_store_forgets_old_keys():
    store = MemoryStore()
    limit = SlidingWindow("public", 5, 0, store)
    limit.add("a")
    for _ in range(1000):
        limit.full("b")
    assert "public:a" not in store.hits
