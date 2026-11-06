"""Регрессионные тесты по итогам QA-ревью.

Каждый тест описывает ОЖИДАЕМОЕ поведение. Пока баг не исправлен, тест падает.
После исправления он должен пройти и дальше защищать от повторения.
"""

from datetime import datetime, timedelta

from conftest import PHONE, login

ORDER = {"name": "Иван", "phone": PHONE, "mode": "pickup"}


def tomorrow(hour: int, minute: int = 0) -> str:
    d = datetime.now() + timedelta(days=1)
    return d.replace(hour=hour, minute=minute, second=0, microsecond=0).isoformat()


# ---------- BUG-01: подмена цены через ref с модификатором ----------

def test_price_cannot_be_faked_with_modifier_ref(client, owner):
    r = client.post("/api/v1/sites/miniapp/orders", json={
        **ORDER, "items": [{"ref": "9:1", "name": "Сет «Лис»", "qty": 10, "price": 1}],
    })
    assert r.status_code in (201, 422), r.text
    if r.status_code == 201:
        orders = client.get("/api/v1/admin/orders", headers=owner).json()["items"]
        assert orders[0]["total"] >= 1590 * 10, f"Сет за 1590 ₽ продан за {orders[0]['total']} ₽"


# ---------- BUG-02: позиция, которой нет в каталоге, продаётся по цене клиента ----------

def test_unknown_ref_rejected_on_catalog_site(client):
    r = client.post("/api/v1/sites/sushi/orders", json={
        **ORDER, "items": [{"ref": "fake", "name": "Сет «Кайсэн»", "qty": 1, "price": 0}],
    })
    assert r.status_code == 422, "Заказ несуществующей позиции по цене 0 ₽ принят"


# ---------- BUG-03: повторное подтверждение отменённой записи даёт двойную запись ----------

def test_reconfirm_cancelled_booking_does_not_double_book(client, owner):
    slot = {"resource": "Артём", "service": "Стрижка", "starts_at": tomorrow(15), "name": "А", "phone": PHONE}
    first = client.post("/api/v1/sites/barbershop/bookings", json=slot).json()["id"]
    client.patch(f"/api/v1/admin/bookings/{first}", json={"status": "cancelled"}, headers=owner)
    assert client.post("/api/v1/sites/barbershop/bookings", json={**slot, "name": "Б"}).status_code == 201
    r = client.patch(f"/api/v1/admin/bookings/{first}", json={"status": "confirmed"}, headers=owner)
    assert r.status_code == 409, "На 15:00 к одному мастеру теперь две подтверждённые записи"


# ---------- BUG-04: запись на произвольную минуту, вне сетки слотов ----------

def test_booking_outside_slot_grid_rejected(client):
    base = {"resource": "Артём", "service": "Стрижка", "name": "А", "phone": PHONE}
    assert client.post("/api/v1/sites/barbershop/bookings", json={**base, "starts_at": tomorrow(15, 0)}).status_code == 201
    r = client.post("/api/v1/sites/barbershop/bookings", json={**base, "starts_at": tomorrow(15, 7)})
    assert r.status_code == 422, "Мастер записан на 15:00 и 15:07 одновременно"


def test_booking_at_night_rejected(client):
    r = client.post("/api/v1/sites/barbershop/bookings", json={
        "resource": "Артём", "starts_at": tomorrow(3, 0), "name": "А", "phone": PHONE})
    assert r.status_code == 422, "Принята запись на 03:00"


def test_booking_far_future_rejected(client):
    r = client.post("/api/v1/sites/barbershop/bookings", json={
        "resource": "Артём", "starts_at": "2099-01-01T15:00:00", "name": "А", "phone": PHONE})
    assert r.status_code == 422, "Принята запись на 2099 год"


# ---------- BUG-05: групповое занятие без лимита мест ----------

def test_group_class_has_capacity_limit(client):
    slot = {"resource": "Йога", "starts_at": tomorrow(19), "name": "А", "phone": PHONE}
    codes = [client.post("/api/v1/sites/fitness/bookings", json=slot).status_code for _ in range(5)]
    # rate limit в тестах = 5, поэтому проверяем через базу: мест в зале не бесконечно
    from app.db import SessionLocal
    from app.models import Booking
    with SessionLocal() as db:
        n = db.query(Booking).filter_by(site="fitness", resource="Йога").count()
    assert n < 5 or 409 in codes, "Сервер не знает вместимость зала, можно записать сколько угодно"


# ---------- BUG-06: CSV-инъекция в выгрузке заявок ----------

def test_csv_export_neutralizes_formulas(client, owner):
    client.post("/api/v1/sites/cafe/leads", json={
        "kind": "callback", "name": '=HYPERLINK("http://evil.example","Нажми")', "phone": PHONE})
    import csv
    import io
    text = client.get("/api/v1/admin/leads.csv", headers=owner).text.lstrip("\ufeff")
    cells = [c for row in csv.reader(io.StringIO(text), delimiter=";") for c in row]
    assert not any(c.startswith("=HYPERLINK") for c in cells), "Формула из имени клиента попадёт в Excel как есть"


# ---------- BUG-07: безлимитное поле data в заявке ----------

def test_lead_data_size_limited(client):
    r = client.post("/api/v1/sites/cafe/leads", json={
        "kind": "callback", "phone": PHONE, "data": {"x": "A" * 2_000_000}})
    assert r.status_code in (413, 422), "Заявка с 2 МБ мусора в data сохранена в базу"


# ---------- BUG-08: перебор пароля без ограничений ----------

def test_login_bruteforce_is_limited(client):
    codes = [client.post("/api/v1/auth/login", json={"email": "owner@test.dev", "password": f"x{i}"}).status_code
             for i in range(30)]
    assert 429 in codes, "30 неверных паролей подряд без блокировки"


# ---------- BUG-09: статус чужого заказа по порядковому номеру ----------

def test_order_status_not_enumerable(client):
    client.post("/api/v1/sites/sushi/orders", json={**ORDER, "items": [{"ref": "s1", "name": "x", "qty": 1, "price": 0}]})
    r = client.get("/api/v1/sites/sushi/orders/1")
    assert r.status_code == 404, f"Любой видит сумму заказа №1: {r.json()}"


# ---------- BUG-10: два товара с одинаковым ref в каталоге ----------

def test_duplicate_catalog_ref_rejected(client, owner):
    r = client.post("/api/v1/admin/catalog/sushi", headers=owner,
                    json={"ref": "s1", "name": "Дубль", "price": 1})
    assert r.status_code == 409, "Второй товар с ref=s1: цена и стоп-лист станут непредсказуемыми"


# ---------- BUG-11: e-mail в заявке не проверяется ----------

def test_lead_email_validated(client):
    r = client.post("/api/v1/sites/cafe/leads", json={"kind": "callback", "email": "a"})
    assert r.status_code == 422, "Заявка с e-mail «a» принята, связаться с клиентом нельзя"


# ---------- Контроль: то, что уже работает правильно ----------

def test_staff_cannot_see_other_sites(client, owner):
    client.post("/api/v1/admin/users", headers=owner, json={
        "email": "s@test.dev", "name": "S", "password": "password1", "role": "staff", "sites": ["cafe"]})
    staff = login(client, "s@test.dev", "password1")
    assert client.get("/api/v1/admin/leads?site=dental", headers=staff).status_code == 403
    assert client.get("/api/v1/admin/users", headers=staff).status_code == 403


# ---------- BUG-10: «время уже прошло» проверяется по часам сервера (UTC), а не заведения ----------

def test_past_local_time_rejected(client):
    # Сайт шлёт «настенное» московское время без пояса. Час назад по Москве = UTC+2 часа.
    msk_hour_ago = (datetime.utcnow() + timedelta(hours=2)).replace(second=0, microsecond=0).isoformat()
    r = client.post("/api/v1/sites/barbershop/bookings", json={
        "resource": "Денис", "starts_at": msk_hour_ago, "name": "А", "phone": PHONE})
    assert r.status_code == 422, "Запись на время, которое в Москве прошло час назад, принята"
