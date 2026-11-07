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
from app.routers.public import check_slot, site_now
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
    day = site_now(site).date() + timedelta(days=case["day_offset"])
    starts_at = datetime.combine(day, time.fromisoformat(case["time"]))
    if case["error"]:
        with pytest.raises(HTTPException) as e:
            check_slot(site, case["resource"], starts_at)
        assert e.value.detail == case["error"]
    else:
        check_slot(site, case["resource"], starts_at)
