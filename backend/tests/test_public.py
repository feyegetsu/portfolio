from datetime import datetime, timedelta

from conftest import PHONE

TOMORROW = (datetime.now() + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


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
    status = client.get(f"/api/v1/sites/miniapp/orders/{r.json()['token']}").json()
    assert status["total"] == 549 * 2

    catalog = client.get("/api/v1/admin/catalog", params={"site": "miniapp"}, headers=owner).json()
    margarita = next(c for c in catalog if c["ref"] == "1")
    client.patch(f"/api/v1/admin/catalog/item/{margarita['id']}", json={"active": False}, headers=owner)
    assert client.post("/api/v1/sites/miniapp/orders", json=body).status_code == 409


def test_modified_item_checks_base_stop_list(client, owner):
    catalog = client.get("/api/v1/admin/catalog", params={"site": "miniapp"}, headers=owner).json()
    pepperoni = next(c for c in catalog if c["ref"] == "2")
    body = {"items": [{"ref": "2:2:0", "name": "Пепперони (35 см)", "qty": 1, "price": 1}], "name": "Иван", "phone": PHONE, "mode": "pickup"}
    r = client.post("/api/v1/sites/miniapp/orders", json=body)
    # 649 ₽ пицца + 170 ₽ за 35 см + 90 ₽ двойной сыр: цену с модификаторами считает сервер, а не браузер
    assert client.get(f"/api/v1/sites/miniapp/orders/{r.json()['token']}").json()["total"] == 649 + 170 + 90
    client.patch(f"/api/v1/admin/catalog/item/{pepperoni['id']}", json={"active": False}, headers=owner)
    assert client.post("/api/v1/sites/miniapp/orders", json=body).status_code == 409


def test_delivery_needs_address(client):
    body = {"items": [{"ref": "2", "name": "Тюльпаны микс", "qty": 1}], "name": "Иван", "phone": PHONE, "mode": "delivery"}
    assert client.post("/api/v1/sites/florist/orders", json=body).status_code == 422
    body["address"] = "ул. Примерная, 1"
    assert client.post("/api/v1/sites/florist/orders", json=body).status_code == 201


def test_restaurant_table_is_not_exclusive(client):
    # В ресторане на одно время бронируют несколько столов, в отличие от мастера барбершопа
    # Понедельник у ресторана выходной: берём ближайший вторник
    evening = next(TOMORROW + timedelta(days=k) for k in range(7) if (TOMORROW + timedelta(days=k)).weekday() == 1).replace(hour=19)
    assert _book(client, site="restaurant", resource="Стол на 2", when=evening).status_code == 201
    assert _book(client, site="restaurant", resource="Стол на 2", when=evening).status_code == 201


def test_sushi_catalog_seeded_and_delivery_counted_by_server(client):
    catalog = client.get("/api/v1/sites/sushi/catalog").json()
    assert len(catalog) == 17
    items = [{"ref": "s4", "name": "Филадельфия", "qty": 1, "price": 1},  # цену берём из каталога
             {"ref": "delivery", "name": "Доставка", "qty": 1, "price": 0}]  # доставку из запроса игнорируем
    body = {"items": items, "name": "Иван", "phone": PHONE, "mode": "delivery", "address": "ул. Примерная, 1"}
    r = client.post("/api/v1/sites/sushi/orders", json=body)
    assert client.get(f"/api/v1/sites/sushi/orders/{r.json()['token']}").json()["total"] == 590 + 199


def test_duplicate_lines_cannot_bypass_quantity_limit(client):
    # BUG-014: 50 одинаковых строк по 99 штук проходили как заказ на 4 950 сетов
    body = {"items": [{"ref": "s2", "qty": 99}] * 50, "name": "Иван", "phone": PHONE, "mode": "pickup"}
    assert client.post("/api/v1/sites/sushi/orders", json=body).status_code == 422


def test_blank_name_rejected(client):
    # BUG-015: min_length считался до обрезки пробелов, и в админку попадали записи без имени
    booking = {"resource": "Артём", "starts_at": TOMORROW.isoformat(), "name": "   ", "phone": PHONE}
    assert client.post("/api/v1/sites/barbershop/bookings", json=booking).status_code == 422
    assert client.post("/api/v1/sites/barbershop/bookings", json={**booking, "name": "Иван", "resource": "  "}).status_code == 422
    order = {"items": [{"ref": "s1", "qty": 1}], "name": " \t ", "phone": PHONE, "mode": "pickup"}
    assert client.post("/api/v1/sites/sushi/orders", json=order).status_code == 422
    assert client.post("/api/v1/sites/cafe/leads", json={"kind": "   ", "phone": PHONE}).status_code == 422
    ok = client.post("/api/v1/sites/barbershop/bookings", json={**booking, "name": "  Иван  "})
    assert ok.status_code == 201


def _next_weekday(weekday: int, hour: int) -> datetime:
    d = TOMORROW
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d.replace(hour=hour, minute=0)


def test_availability(client, monkeypatch):
    # BUG-005: формы показывают настоящую занятость, а не формулу от даты
    from app.limits import rate_limit
    monkeypatch.setattr(rate_limit, "limit", 100)
    when = _next_weekday(1, 20)  # вторник, ресторан открыт
    for _ in range(10):
        assert _book(client, site="restaurant", resource="Стол на 2", when=when).status_code == 201
    slots = client.get("/api/v1/sites/restaurant/availability", params={"date": when.date().isoformat()}).json()
    by_time = {s["time"]: s for s in slots}
    assert by_time["20:00"]["left"] == 0
    assert by_time["19:30"]["left"] == 10
    assert by_time["20:00"]["starts_at"] == when.isoformat()
    assert [s["time"] for s in slots][0] == "18:00" and slots[-1]["time"] == "22:30"
    monday = _next_weekday(0, 19).date().isoformat()
    assert client.get("/api/v1/sites/restaurant/availability", params={"date": monday}).json() == []  # выходной


def test_availability_per_class_and_master(client):
    when = TOMORROW.replace(hour=19, minute=30)
    _book(client, site="fitness", resource="Тайский бокс", when=when)
    day = when.date().isoformat()
    fitness = client.get("/api/v1/sites/fitness/availability", params={"date": day, "resource": "Тайский бокс"}).json()
    assert {s["time"]: s["left"] for s in fitness}["19:30"] == 9
    assert client.get("/api/v1/sites/fitness/availability", params={"date": day}).status_code == 422  # у фитнеса нужно занятие
    _book(client, resource="Артём")  # TOMORROW 15:00
    barber = client.get("/api/v1/sites/barbershop/availability", params={"date": day, "resource": "Артём"}).json()
    assert {s["time"]: s["left"] for s in barber}["15:00"] == 0
    assert {s["time"]: s["left"] for s in barber}["16:00"] == 1
    assert client.get("/api/v1/sites/cafe/availability", params={"date": day}).status_code == 404
