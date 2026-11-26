from conftest import PHONE, login


def test_login_and_me(client, owner):
    me = client.get("/api/v1/auth/me", headers=owner).json()
    assert me["role"] == "owner"
    assert me["sites"] is None


def test_wrong_password(client):
    r = client.post("/api/v1/auth/login", json={"email": "owner@test.dev", "password": "nope"})
    assert r.status_code == 401


def test_admin_requires_token(client):
    assert client.get("/api/v1/admin/leads").status_code == 401
    assert client.get("/api/v1/admin/leads", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_lead_filters_and_status(client, owner):
    client.post("/api/v1/sites/cafe/leads", json={"kind": "table", "name": "Анна", "phone": PHONE})
    client.post("/api/v1/sites/dental/leads", json={"kind": "consult", "name": "Борис", "phone": PHONE})

    assert client.get("/api/v1/admin/leads", headers=owner).json()["total"] == 2
    assert client.get("/api/v1/admin/leads", params={"site": "dental"}, headers=owner).json()["total"] == 1
    found = client.get("/api/v1/admin/leads", params={"q": "Анна"}, headers=owner).json()
    assert [i["name"] for i in found["items"]] == ["Анна"]

    lead_id = found["items"][0]["id"]
    assert client.patch(f"/api/v1/admin/leads/{lead_id}", json={"status": "done"}, headers=owner).json()["status"] == "done"
    assert client.patch(f"/api/v1/admin/leads/{lead_id}", json={"status": "weird"}, headers=owner).status_code == 422


def test_staff_sees_only_own_sites_and_cannot_manage(client, owner):
    r = client.post("/api/v1/admin/users", headers=owner, json={
        "email": "barista@test.dev", "name": "Бариста", "password": "password123", "role": "staff", "sites": ["cafe"],
    })
    assert r.status_code == 201
    staff = login(client, "barista@test.dev", "password123")

    client.post("/api/v1/sites/cafe/leads", json={"kind": "table", "phone": PHONE})
    client.post("/api/v1/sites/dental/leads", json={"kind": "consult", "phone": PHONE})

    assert client.get("/api/v1/admin/leads", headers=staff).json()["total"] == 1
    assert client.get("/api/v1/admin/leads", params={"site": "dental"}, headers=staff).status_code == 403
    assert client.get("/api/v1/admin/users", headers=staff).status_code == 403
    assert client.post("/api/v1/admin/catalog/miniapp", headers=staff, json={"ref": "x", "name": "x", "price": 1}).status_code == 403


def test_duplicate_user(client, owner):
    body = {"email": "a@test.dev", "name": "A", "password": "password123"}
    assert client.post("/api/v1/admin/users", json=body, headers=owner).status_code == 201
    assert client.post("/api/v1/admin/users", json=body, headers=owner).status_code == 409


def test_owner_cannot_delete_self(client, owner):
    me = client.get("/api/v1/auth/me", headers=owner).json()
    assert client.delete(f"/api/v1/admin/users/{me['id']}", headers=owner).status_code == 422


def test_stats(client, owner):
    client.post("/api/v1/sites/cafe/leads", json={"kind": "table", "phone": PHONE})
    client.post("/api/v1/sites/florist/orders", json={
        "items": [{"ref": "8", "name": "Кактус в кашпо", "qty": 2}], "name": "Иван", "phone": PHONE, "mode": "pickup",
    })
    s = client.get("/api/v1/admin/stats", headers=owner).json()
    assert (s["leads"], s["orders"], s["revenue"], s["new_leads"]) == (1, 1, 3000, 1)
    assert sum(d["count"] for d in s["by_day"]) == 2
    assert s["by_site"] == {"cafe": 1, "florist": 1}


def test_csv_export(client, owner):
    client.post("/api/v1/sites/cafe/leads", json={"kind": "table", "name": "Анна", "phone": PHONE})
    r = client.get("/api/v1/admin/leads.csv", headers=owner)
    assert r.status_code == 200
    assert r.text.startswith("﻿id;Дата;Сайт")
    assert "Анна" in r.text


def test_password_rehash_on_login(client):
    # SEC-010: хеш со старым числом итераций пересчитывается при удачном входе
    from app.config import settings
    from app.db import SessionLocal
    from app.models import User
    from app.security import hash_password

    old = max(1, settings.password_iterations // 2)
    with SessionLocal() as db:
        owner = db.query(User).filter_by(email="owner@test.dev").one()
        owner.password_hash = hash_password("owner-password", iterations=old)
        db.commit()
    login(client)
    with SessionLocal() as db:
        stored = db.query(User).filter_by(email="owner@test.dev").one().password_hash
    assert int(stored.split("$")[1]) == settings.password_iterations
    login(client)  # новый хеш проверяется


def test_production_requires_owasp_iterations():
    from dataclasses import replace

    import pytest

    from app.config import check_secrets, settings
    with pytest.raises(RuntimeError, match="PASSWORD_ITERATIONS"):
        check_secrets(replace(settings, env="production", password_iterations=390_000))
    check_secrets(replace(settings, env="production", password_iterations=600_000))


def test_catalog_price_must_be_positive(client, owner):
    # BUG-007: пустое поле цены в админке превращалось в 0, и позиция продавалась бесплатно
    item = client.get("/api/v1/admin/catalog", params={"site": "sushi"}, headers=owner).json()[0]
    assert client.patch(f"/api/v1/admin/catalog/item/{item['id']}", json={"price": 0}, headers=owner).status_code == 422
    assert client.post("/api/v1/admin/catalog/sushi", json={"ref": "free", "name": "Даром", "price": 0}, headers=owner).status_code == 422
    assert client.patch(f"/api/v1/admin/catalog/item/{item['id']}", json={"price": 1}, headers=owner).status_code == 200


def test_search_case_insensitive_and_escaped(client, owner):
    # BUG-009: в SQLite ILIKE не приводит кириллицу к нижнему регистру, а % и _ находили всё
    for name in ("Анна", "Борис", "Вера"):
        client.post("/api/v1/sites/cafe/leads", json={"kind": "table", "name": name, "phone": PHONE, "message": "Столик у окна"})
    total = lambda q: client.get("/api/v1/admin/leads", params={"q": q}, headers=owner).json()["total"]  # noqa: E731
    assert [total(q) for q in ("Анна", "анна", "%", "_")] == [1, 1, 0, 0]
    assert total("СТОЛИК") == 3
    assert total("+7900") == 3  # телефон хранится нормализованным


def _lead_at(created_at):
    from app.db import SessionLocal
    from app.models import Lead
    with SessionLocal() as db:
        db.add(Lead(site="cafe", kind="table", name="Ночной", phone="+79001234567", created_at=created_at))
        db.commit()


def test_csv_dates_in_site_timezone(client, owner):
    # BUG-010: created_at хранится в UTC, а владелец ждёт московское время
    from datetime import datetime
    _lead_at(datetime(2026, 11, 17, 22, 30))
    text = client.get("/api/v1/admin/leads.csv", headers=owner).text
    assert "18.11.2026 01:30" in text


def test_stats_days_in_site_timezone(client, owner):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    msk_today = datetime.now(ZoneInfo("Europe/Moscow")).date()
    # 00:30 по Москве сегодня — это ещё вчера по UTC
    _lead_at(datetime.combine(msk_today, datetime.min.time()) + timedelta(minutes=30) - timedelta(hours=3))
    by_day = {d["date"]: d["count"] for d in client.get("/api/v1/admin/stats", headers=owner).json()["by_day"]}
    assert by_day[msk_today.isoformat()] == 1
    assert max(by_day) == msk_today.isoformat()


def _user(client, owner, **kw):
    body = {"email": "u@test.dev", "name": "U", "password": "password123", **kw}
    return client.post("/api/v1/admin/users", json=body, headers=owner)


def test_user_validation(client, owner):
    # BE-002: e-mail с опечаткой и пустой список сайтов делали учётку бесполезной
    assert _user(client, owner, email="abc").status_code == 422
    assert _user(client, owner, sites=[]).status_code == 422
    assert _user(client, owner, sites=["nope"]).status_code == 422
    assert _user(client, owner, sites=["cafe"]).status_code == 201


def test_update_user_role(client, owner):
    staff = _user(client, owner, sites=["cafe"]).json()
    token = login(client, "u@test.dev", "password123")
    r = client.patch(f"/api/v1/admin/users/{staff['id']}", headers=owner, json={"role": "admin", "sites": ["cafe", "dental"]})
    assert r.status_code == 200
    assert (r.json()["role"], r.json()["sites"]) == ("admin", ["cafe", "dental"])
    assert client.get("/api/v1/auth/me", headers=token).status_code == 401  # права поменялись — старый токен гаснет
    r = client.patch(f"/api/v1/admin/users/{staff['id']}", headers=owner, json={"password": "another-pass-1"})
    assert r.status_code == 200
    login(client, "u@test.dev", "another-pass-1")
    assert client.patch("/api/v1/admin/users/999", headers=owner, json={"name": "X"}).status_code == 404
    assert client.patch(f"/api/v1/admin/users/{staff['id']}", headers=owner, json={"sites": []}).status_code == 422


def test_last_owner_is_protected(client, owner):
    me = client.get("/api/v1/auth/me", headers=owner).json()
    r = client.patch(f"/api/v1/admin/users/{me['id']}", headers=owner, json={"role": "admin"})
    assert r.status_code == 422, "Единственный владелец снял с себя роль — командой больше некому управлять"
    second = _user(client, owner, email="o2@test.dev", role="owner").json()
    assert client.delete(f"/api/v1/admin/users/{second['id']}", headers=owner).status_code == 204
    assert client.delete("/api/v1/admin/users/999", headers=owner).status_code == 404
    third = _user(client, owner, email="o3@test.dev", role="owner").json()
    # Владельцев двое: понизить себя можно, второй остаётся
    assert client.patch(f"/api/v1/admin/users/{me['id']}", headers=owner, json={"role": "admin"}).status_code == 200
    o3 = login(client, "o3@test.dev", "password123")
    assert client.patch(f"/api/v1/admin/users/{third['id']}", headers=o3, json={"role": "staff", "sites": ["cafe"]}).status_code == 422


def test_bookings_date_range(client, owner):
    # BUG-008: админка брала 100 последних созданных записей, и ранние визиты пропадали из расписания
    from datetime import datetime, timedelta

    from app.db import SessionLocal
    from app.models import Booking
    start = datetime(2027, 3, 1, 12, 0)
    with SessionLocal() as db:
        for i in range(150):  # по 5 записей на 30 дней, созданы в обратном порядке
            when = start + timedelta(days=i // 5, hours=i % 5)
            db.add(Booking(site="restaurant", resource="Стол на 2", starts_at=when, name=f"Гость {i}", phone="+79001234567",
                           created_at=datetime(2026, 1, 1) + timedelta(minutes=150 - i)))
        db.commit()
    r = client.get("/api/v1/admin/bookings", params={"date_from": "2027-03-08", "date_to": "2027-03-14", "limit": 200}, headers=owner)
    data = r.json()
    assert data["total"] == 35
    times = [b["starts_at"] for b in data["items"]]
    assert times == sorted(times) and times[0].startswith("2027-03-08") and times[-1].startswith("2027-03-14")
    assert client.get("/api/v1/admin/bookings", params={"date_from": "2027-03-14", "date_to": "2027-03-08"}, headers=owner).json()["total"] == 0


def test_orders_paginated(client, owner, monkeypatch):
    from app.limits import rate_limit
    monkeypatch.setattr(rate_limit, "limit", 100)
    for _ in range(7):
        client.post("/api/v1/sites/sushi/orders", json={"items": [{"ref": "s7", "qty": 1}], "name": "И", "phone": PHONE, "mode": "pickup"})
    page = client.get("/api/v1/admin/orders", params={"limit": 5, "offset": 5}, headers=owner).json()
    assert page["total"] == 7 and len(page["items"]) == 2


def test_order_status_and_filter(client, owner):
    # TEST-002: смена статуса заказа и фильтр по статусу
    r = client.post("/api/v1/sites/sushi/orders", json={"items": [{"ref": "s7", "qty": 1}], "name": "И", "phone": PHONE, "mode": "pickup"})
    order_id = r.json()["id"]
    assert client.patch(f"/api/v1/admin/orders/{order_id}", json={"status": "cooking"}, headers=owner).json()["status"] == "cooking"
    assert client.get("/api/v1/admin/orders", params={"status": "cooking"}, headers=owner).json()["total"] == 1
    assert client.get("/api/v1/admin/orders", params={"status": "done"}, headers=owner).json()["total"] == 0
    assert client.patch("/api/v1/admin/orders/999", json={"status": "done"}, headers=owner).status_code == 404


def test_catalog_item_delete_and_unknown_site(client, owner):
    item = client.get("/api/v1/admin/catalog", params={"site": "florist"}, headers=owner).json()[0]
    assert client.delete(f"/api/v1/admin/catalog/item/{item['id']}", headers=owner).status_code == 204
    assert client.delete(f"/api/v1/admin/catalog/item/{item['id']}", headers=owner).status_code == 404
    assert client.post("/api/v1/admin/catalog/cafe", json={"ref": "x", "name": "x", "price": 1}, headers=owner).status_code == 404


def test_list_users_and_remove(client, owner):
    u = _user(client, owner, sites=["cafe"]).json()
    assert [x["email"] for x in client.get("/api/v1/admin/users", headers=owner).json()] == ["owner@test.dev", "u@test.dev"]
    assert client.delete(f"/api/v1/admin/users/{u['id']}", headers=owner).status_code == 204
    assert client.delete(f"/api/v1/admin/users/{u['id']}", headers=owner).status_code == 404


def test_upcoming_bookings_and_cancel_booking(client, owner):
    from datetime import datetime, timedelta
    when = (datetime.now() + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
    b = client.post("/api/v1/sites/barbershop/bookings", json={"resource": "Денис", "starts_at": when, "name": "И", "phone": PHONE}).json()
    assert client.get("/api/v1/admin/bookings", params={"upcoming": True}, headers=owner).json()["total"] == 1
    client.patch(f"/api/v1/admin/bookings/{b['id']}", json={"status": "cancelled"}, headers=owner)
    assert client.get("/api/v1/admin/bookings", params={"upcoming": True}, headers=owner).json()["total"] == 0
