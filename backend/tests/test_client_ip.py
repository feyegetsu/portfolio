"""SEC-001: IP посетителя берётся по числу доверенных прокси справа, а не из первого элемента X-Forwarded-For."""

from dataclasses import replace

import pytest
from conftest import PHONE

from app import deps

LEAD = {"kind": "table", "phone": PHONE}


@pytest.fixture
def behind_proxy(monkeypatch):
    monkeypatch.setattr(deps, "settings", replace(deps.settings, trusted_proxy_hops=1))


def test_spoofed_first_hop_does_not_bypass_rate_limit(client, behind_proxy):
    # Злоумышленник меняет первый элемент, балансировщик дописывает реальный адрес последним
    codes = [
        client.post("/api/v1/sites/cafe/leads", json=LEAD, headers={"X-Forwarded-For": f"10.0.0.{i}, 203.0.113.1"}).status_code
        for i in range(6)
    ]
    assert codes == [201] * 5 + [429]


def test_different_real_clients_have_separate_limits(client, behind_proxy):
    for _ in range(5):
        client.post("/api/v1/sites/cafe/leads", json=LEAD, headers={"X-Forwarded-For": "203.0.113.1"})
    r = client.post("/api/v1/sites/cafe/leads", json=LEAD, headers={"X-Forwarded-For": "203.0.113.2"})
    assert r.status_code == 201


def test_without_proxy_header_falls_back_to_socket_address(client, behind_proxy):
    codes = [client.post("/api/v1/sites/cafe/leads", json=LEAD).status_code for _ in range(6)]
    assert codes[-1] == 429


def test_header_ignored_when_no_trusted_proxies(client):
    # По умолчанию (TRUSTED_PROXY_HOPS=0) заголовку не верим вовсе
    codes = [
        client.post("/api/v1/sites/cafe/leads", json=LEAD, headers={"X-Forwarded-For": f"10.0.0.{i}"}).status_code
        for i in range(6)
    ]
    assert codes[-1] == 429


def test_client_ip_picks_hop_from_the_right():
    class Req:
        def __init__(self, xff):
            self.headers = {"x-forwarded-for": xff} if xff else {}
            self.client = type("C", (), {"host": "10.9.9.9"})()

    s = replace(deps.settings, trusted_proxy_hops=2)
    assert deps.client_ip(Req("1.1.1.1, 2.2.2.2, 3.3.3.3"), s) == "2.2.2.2"
    assert deps.client_ip(Req("3.3.3.3"), s) == "10.9.9.9"  # цепочка короче числа прокси — заголовок подделан
    assert deps.client_ip(Req(""), s) == "10.9.9.9"
