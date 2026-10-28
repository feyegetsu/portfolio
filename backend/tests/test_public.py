from datetime import datetime, timedelta

from conftest import PHONE

TOMORROW = (datetime.now() + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_create_lead_normalizes_phone(client, owner):
    r = client.post("/api/v1/sites/cafe/leads", json={"kind": "table", "name": "Анна", "phone": PHONE, "data": {"guests": 2}})
    assert r.status_code == 201
    lead = client.get("/api/v1/admin/leads", headers=owner).json()["items"][0]
    assert lead["phone"] == "+79001234567"
    assert lead["data"] == {"guests": 2}


def test_lead_requires_contact(client):
    r = client.post("/api/v1/sites/cafe/leads", json={"kind": "table", "name": "Анна"})
    assert r.status_code == 422


def test_bad_phone_rejected(client):
    r = client.post("/api/v1/sites/cafe/leads", json={"kind": "table", "phone": "12"})
    assert r.status_code == 422


def test_unknown_site_and_feature(client):
    assert client.post("/api/v1/sites/nope/leads", json={"kind": "x", "phone": PHONE}).status_code == 404
    # у барбершопа нет заявок, только запись
    assert client.post("/api/v1/sites/barbershop/leads", json={"kind": "x", "phone": PHONE}).status_code == 404


def test_honeypot_is_silently_dropped(client, owner):
    r = client.post("/api/v1/sites/cafe/leads", json={"kind": "table", "phone": PHONE, "website": "http://spam"})
    assert r.status_code == 201
    assert client.get("/api/v1/admin/leads", headers=owner).json()["total"] == 0


def test_rate_limit(client):
    payload = {"kind": "table", "phone": PHONE}
    codes = [client.post("/api/v1/sites/cafe/leads", json=payload).status_code for _ in range(6)]
    assert codes[:5] == [201] * 5
    assert codes[5] == 429


def _book(client, site="barbershop", when=TOMORROW, resource="Артём"):
    return client.post(f"/api/v1/sites/{site}/bookings", json={
        "resource": resource, "service": "Стрижка", "starts_at": when.isoformat(), "name": "Иван", "phone": PHONE,
    })


def test_exclusive_slot_cannot_be_double_booked(client):
    assert _book(client).status_code == 201
    assert _book(client).status_code == 409
    assert _book(client, resource="Денис").status_code == 201  # другой мастер свободен
    busy = client.get("/api/v1/sites/barbershop/slots", params={"resource": "Артём", "date": TOMORROW.date().isoformat()}).json()
    assert busy == ["15:00"]


def test_group_class_allows_many(client):
    assert _book(client, site="fitness", resource="Кроссфит").status_code == 201
    assert _book(client, site="fitness", resource="Кроссфит").status_code == 201


def test_cancel_frees_slot(client, owner):
    booking_id = _book(client).json()["id"]
    r = client.patch(f"/api/v1/admin/bookings/{booking_id}", json={"status": "cancelled"}, headers=owner)
    assert r.status_code == 200
    assert _book(client).status_code == 201


def test_past_booking_rejected(client):
    assert _book(client, when=datetime.now() - timedelta(days=1)).status_code == 422


def test_order_uses_catalog_price_and_stop_list(client, owner):
    items = [{"ref": "1", "name": "Маргарита", "qty": 2, "price": 1}]  # клиент пытается подменить цену
    body = {"items": items, "name": "Иван", "phone": PHONE, "mode": "pickup"}
    r = client.post("/api/v1/sites/miniapp/orders", json=body)
    assert r.status_code == 201
    status = client.get(f"/api/v1/sites/miniapp/orders/{r.json()['id']}").json()
    assert status["total"] == 549 * 2

    catalog = client.get("/api/v1/admin/catalog", params={"site": "miniapp"}, headers=owner).json()
    margarita = next(c for c in catalog if c["ref"] == "1")
    client.patch(f"/api/v1/admin/catalog/item/{margarita['id']}", json={"active": False}, headers=owner)
    assert client.post("/api/v1/sites/miniapp/orders", json=body).status_code == 409


def test_modified_item_checks_base_stop_list(client, owner):
    catalog = client.get("/api/v1/admin/catalog", params={"site": "miniapp"}, headers=owner).json()
    pepperoni = next(c for c in catalog if c["ref"] == "2")
    body = {"items": [{"ref": "2:2:0", "name": "Пепперони (35 см)", "qty": 1, "price": 819}], "name": "Иван", "phone": PHONE, "mode": "pickup"}
    r = client.post("/api/v1/sites/miniapp/orders", json=body)
    assert client.get(f"/api/v1/sites/miniapp/orders/{r.json()['id']}").json()["total"] == 819  # цена с модификатором сохраняется
    client.patch(f"/api/v1/admin/catalog/item/{pepperoni['id']}", json={"active": False}, headers=owner)
    assert client.post("/api/v1/sites/miniapp/orders", json=body).status_code == 409


def test_delivery_needs_address(client):
    body = {"items": [{"name": "Букет", "qty": 1, "price": 3000}], "name": "Иван", "phone": PHONE, "mode": "delivery"}
    assert client.post("/api/v1/sites/florist/orders", json=body).status_code == 422
    body["address"] = "ул. Примерная, 1"
    assert client.post("/api/v1/sites/florist/orders", json=body).status_code == 201
