"""SEC-003: перебор пароля ограничен по аккаунту и по IP, а без Redis вход закрывается, а не открывается."""

from dataclasses import replace

import fakeredis
import pytest
from conftest import PHONE

from app import deps
from app.limits import RedisStore, login_account_limit, login_ip_limit, login_limit, rate_limit

LOGIN = "/api/v1/auth/login"


@pytest.fixture
def behind_proxy(monkeypatch):
    monkeypatch.setattr(deps, "settings", replace(deps.settings, trusted_proxy_hops=1))


def attempt(client, ip, email="owner@test.dev", password="wrong"):
    return client.post(LOGIN, json={"email": email, "password": password}, headers={"X-Forwarded-For": ip}).status_code


def test_distributed_bruteforce_on_one_account_is_limited(client, behind_proxy):
    codes = [attempt(client, f"198.51.100.{i}") for i in range(login_account_limit.limit + 1)]
    assert codes[:-1] == [401] * login_account_limit.limit
    assert codes[-1] == 429
    # Аккаунт закрыт для всех IP, в том числе с верным паролем: перебор не узнает, что угадал
    assert attempt(client, "203.0.113.50", password="owner-password") == 429


def test_many_emails_from_one_ip_are_limited(client, behind_proxy):
    codes = [attempt(client, "203.0.113.7", email=f"user{i}@test.dev") for i in range(login_ip_limit.limit + 1)]
    assert codes[-1] == 429
    assert attempt(client, "203.0.113.8", email="other@test.dev") == 401  # другой IP не задет


def test_successful_login_does_not_reset_account_counter(client, behind_proxy):
    for i in range(login_account_limit.limit - 1):
        attempt(client, f"198.51.100.{i}")
    assert attempt(client, "198.51.100.200", password="owner-password") == 200
    assert attempt(client, "198.51.100.201") == 401
    assert attempt(client, "198.51.100.202") == 429


def test_429_tells_how_long_to_wait(client):
    for _ in range(login_limit.limit):
        attempt(client, "x")
    r = client.post(LOGIN, json={"email": "owner@test.dev", "password": "wrong"})
    assert r.status_code == 429
    assert "мин" in r.json()["detail"]


def test_login_closed_but_orders_open_when_redis_is_down(client, monkeypatch):
    server = fakeredis.FakeServer()
    server.connected = False
    down = RedisStore(fakeredis.FakeRedis(server=server))
    for limiter in (login_limit, login_account_limit, login_ip_limit, rate_limit):
        monkeypatch.setattr(limiter, "store", down)

    r = client.post(LOGIN, json={"email": "owner@test.dev", "password": "owner-password"})
    assert r.status_code in (429, 503)
    assert client.post("/api/v1/sites/cafe/leads", json={"kind": "table", "phone": PHONE}).status_code == 201
