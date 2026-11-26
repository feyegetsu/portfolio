"""Сервер и демо-клиент считают одинаково.

Правила для демо генерируются из sites.py и seed.py (app.rules_export), а логику расчёта проверяют общие
примеры tests/parity_cases.json: их же прогоняет node tools/parity.mjs по коду из projects/shared/api.js.
"""

import json
from datetime import datetime, time, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app import rules_export
from app.pricing import price_order
from app.services.booking import check_slot, site_now
from app.db import to_local
from app.schemas import OrderItem
from app.seed import CATALOGS
from app.sites import SITES

CASES = json.loads((Path(__file__).parent / "parity_cases.json").read_text(encoding="utf-8"))


def test_demo_rules_are_generated_from_backend():
    if not rules_export.API_JS.exists():
        pytest.skip("бэкенд запущен отдельно от сайта")
    current = rules_export.extract(rules_export.API_JS.read_text(encoding="utf-8"))
    assert current == rules_export.render(), "Правила в projects/shared/api.js устарели: cd backend && python -m app.rules_export"


@pytest.mark.parametrize("case", CASES["orders"], ids=lambda c: c["title"])
def test_order_pricing(case):
    catalog = {ref: SimpleNamespace(ref=ref, name=name, category=cat, price=price, active=ref not in case["inactive"])
               for ref, name, cat, price in CATALOGS[case["site"]]}
    items = [OrderItem(**i) for i in case["items"]]
    rules = SITES[case["site"]].pricing
    if "error" in case:
        with pytest.raises(HTTPException) as e:
            price_order(items, catalog, rules, case["mode"], case["promo"])
        assert (e.value.status_code, e.value.detail) == (case["error"]["status"], case["error"]["message"])
    else:
        assert price_order(items, catalog, rules, case["mode"], case["promo"]) == case["lines"]


@pytest.mark.parametrize("case", CASES["slots"], ids=lambda c: c["title"])
def test_booking_slot(case):
    site = SITES[case["site"]]
    today = site_now(site).date()
    if "weekday" in case:  # ближайший такой день недели, начиная с завтра
        day = next(today + timedelta(days=k) for k in range(1, 8) if (today + timedelta(days=k)).weekday() == case["weekday"])
    else:
        day = today + timedelta(days=case["day_offset"])
    starts_at = datetime.combine(day, time.fromisoformat(case["time"]))
    if case["error"]:
        with pytest.raises(HTTPException) as e:
            check_slot(site, case["resource"], starts_at)
        assert e.value.detail == case["error"]
    else:
        check_slot(site, case["resource"], starts_at)


# ---------- Поведение API целиком: те же примеры прогоняет демо-движок в tools/parity.mjs ----------

def detail(r) -> str:
    """Текст ошибки так, как его покажет клиент api.js: у ошибок валидации — без префикса «Value error, »."""
    d = r.json().get("detail") if r.content else None
    if isinstance(d, list):
        return "; ".join(x["msg"].removeprefix("Value error, ") for x in d)
    return d or ""


def stored(client, owner, kind: str) -> int:
    return client.get(f"/api/v1/admin/{kind}", headers=owner).json()["total"]


def check_response(case, r, before=None, after=None):
    assert r.status_code == case["status"], (r.status_code, r.text)
    if "message" in case:
        assert detail(r) == case["message"]
    if "stored" in case:
        assert (after > before) == case["stored"]


@pytest.mark.parametrize("case", CASES["leads"], ids=lambda c: c["title"])
def test_lead_rules(case, client, owner):
    before = stored(client, owner, "leads")
    r = client.post(f"/api/v1/sites/{case['site']}/leads", json=case["body"])
    check_response(case, r, before, stored(client, owner, "leads"))


@pytest.mark.parametrize("case", CASES["orders_validation"], ids=lambda c: c["title"])
def test_order_rules(case, client, owner):
    before = stored(client, owner, "orders")
    r = client.post(f"/api/v1/sites/{case['site']}/orders", json=case["body"])
    check_response(case, r, before, stored(client, owner, "orders"))


@pytest.mark.parametrize("case", CASES["bookings"], ids=lambda c: c["title"])
def test_booking_rules(case, client, owner):
    site = SITES[case["site"]]
    today = site_now(site).date()
    day = next(today + timedelta(days=k) for k in range(1, 8) if (today + timedelta(days=k)).weekday() == case["weekday"])
    body = {"resource": case["resource"], "starts_at": f"{day.isoformat()}T{case['time']}:00{case['suffix']}",
            "name": "Иван", "phone": "+79001234567"}
    if "website" in case:
        body["website"] = case["website"]
    before = stored(client, owner, "bookings")
    r = client.post(f"/api/v1/sites/{case['site']}/bookings", json=body)
    check_response(case, r, before, stored(client, owner, "bookings"))


@pytest.mark.parametrize("case", CASES["catalog_patch"], ids=lambda c: c["title"])
def test_catalog_patch_rules(case, client, owner):
    item = next(c for c in client.get("/api/v1/admin/catalog", params={"site": case["site"]}, headers=owner).json()
                if c["ref"] == case["ref"])
    check_response(case, client.patch(f"/api/v1/admin/catalog/item/{item['id']}", json=case["body"], headers=owner))


@pytest.mark.parametrize("case", CASES["users"], ids=lambda c: c["title"])
def test_user_rules(case, client, owner):
    if case["action"] == "add":
        r = client.post("/api/v1/admin/users", json=case["body"], headers=owner)
    else:
        r = client.delete("/api/v1/admin/users/99999", headers=owner)
    check_response(case, r)


@pytest.mark.parametrize("case", CASES["search"], ids=lambda c: c["title"])
def test_search_rules(case, client, owner):
    for name in case["names"]:
        client.post("/api/v1/sites/cafe/leads", json={"kind": "table", "name": name, "phone": "+79001234567"})
    r = client.get("/api/v1/admin/leads", params={"q": case["q"]}, headers=owner)
    assert r.json()["total"] == case["total"]


@pytest.mark.parametrize("case", CASES["csv_dates"], ids=lambda c: c["title"])
def test_csv_dates(case):
    assert to_local(datetime.fromisoformat(case["created_at"]), case["tz"]).strftime("%d.%m.%Y %H:%M") == case["expected"]
