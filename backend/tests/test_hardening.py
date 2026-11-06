"""Проверки к исправлениям по QA-отчёту, которых нет в test_qa_findings.py."""

from dataclasses import replace

import pytest
from conftest import PHONE

from app.config import DEV_PASSWORD, DEV_SECRET, check_secrets, settings

ORDER = {"name": "Иван", "phone": PHONE}


@pytest.mark.parametrize("changes", [
    {"secret_key": DEV_SECRET},
    {"secret_key": "short"},
    {"owner_password": DEV_PASSWORD},
    {"owner_password": "замените-на-надёжный-пароль"},
])
def test_insecure_settings_stop_startup(changes):
    with pytest.raises(RuntimeError):
        check_secrets(replace(settings, env="production", **changes))


def test_development_allows_defaults():
    check_secrets(replace(settings, env="development", secret_key=DEV_SECRET, owner_password=DEV_PASSWORD))


def _total(client, site, body):
    r = client.post(f"/api/v1/sites/{site}/orders", json=body)
    assert r.status_code == 201, r.text
    return client.get(f"/api/v1/sites/{site}/orders/{r.json()['token']}").json()


def test_promo_and_free_delivery_counted_by_server(client):
    # 2 × «Сет Лис» = 3180 ₽, FOX10 −318 ₽, после скидки больше 1500 ₽ — доставка бесплатная
    body = {**ORDER, "mode": "delivery", "address": "ул. Примерная, 1", "promo": " fox10 ",
            "items": [{"ref": "9", "qty": 2, "price": 1}]}
    order = _total(client, "miniapp", body)
    assert order["total"] == 3180 - 318
    assert [i["ref"] for i in order["items"]] == ["9", "promo"]


def test_unknown_promo_rejected(client):
    body = {**ORDER, "mode": "pickup", "promo": "LIS", "items": [{"ref": "9", "qty": 1}]}
    assert client.post("/api/v1/sites/miniapp/orders", json=body).status_code == 422


def test_delivery_added_below_threshold(client):
    body = {**ORDER, "mode": "delivery", "address": "ул. Примерная, 1", "items": [{"ref": "s7", "qty": 1}]}
    assert _total(client, "sushi", body)["total"] == 190 + 199


def test_extras_only_for_pizza(client):
    body = {**ORDER, "mode": "pickup", "items": [{"ref": "5:1:0", "qty": 1}]}  # бургер с «двойным сыром»
    assert client.post("/api/v1/sites/miniapp/orders", json=body).status_code == 422


def test_florist_prices_from_catalog(client):
    body = {**ORDER, "mode": "pickup", "items": [{"ref": "3", "qty": 1, "price": 1}]}
    assert _total(client, "florist", body)["total"] == 8900
