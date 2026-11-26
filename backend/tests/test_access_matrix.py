"""TEST-002: матрица доступа «роль × сайт × эндпоинт» — сотрудник и администратор одного сайта не видят и не меняют чужое."""

import pytest
from conftest import PHONE, login

ORDER = {"name": "Иван", "phone": PHONE, "mode": "pickup"}


@pytest.fixture
def world(client, owner, monkeypatch):
    """Чужие данные на других сайтах и два пользователя кофейни: staff и admin."""
    from app.limits import rate_limit
    monkeypatch.setattr(rate_limit, "limit", 100)
    lead = client.post("/api/v1/sites/dental/leads", json={"kind": "consult", "phone": PHONE}).json()["id"]
    order = client.post("/api/v1/sites/sushi/orders", json={**ORDER, "items": [{"ref": "s7", "qty": 1}]}).json()["id"]
    from datetime import datetime, timedelta
    when = (datetime.now() + timedelta(days=1)).replace(hour=15, minute=0, second=0, microsecond=0).isoformat()
    booking = client.post("/api/v1/sites/barbershop/bookings",
                          json={"resource": "Артём", "starts_at": when, "name": "И", "phone": PHONE}).json()["id"]
    item = next(c for c in client.get("/api/v1/admin/catalog", params={"site": "sushi"}, headers=owner).json() if c["ref"] == "s1")["id"]
    users = {}
    for role in ("staff", "admin"):
        email = f"{role}@cafe.dev"
        client.post("/api/v1/admin/users", headers=owner,
                    json={"email": email, "name": role, "password": "password123", "role": role, "sites": ["cafe"]})
        users[role] = login(client, email, "password123")
    return {"lead": lead, "order": order, "booking": booking, "item": item, "users": users}


FORBIDDEN = [
    ("patch", "/api/v1/admin/leads/{lead}", {"status": "done"}),
    ("patch", "/api/v1/admin/orders/{order}", {"status": "done"}),
    ("patch", "/api/v1/admin/bookings/{booking}", {"status": "cancelled"}),
    ("patch", "/api/v1/admin/catalog/item/{item}", {"price": 1}),
    ("delete", "/api/v1/admin/catalog/item/{item}", None),
    ("post", "/api/v1/admin/catalog/sushi", {"ref": "x", "name": "x", "price": 1}),
    ("get", "/api/v1/admin/leads?site=dental", None),
    ("get", "/api/v1/admin/orders?site=sushi", None),
    ("get", "/api/v1/admin/bookings?site=barbershop", None),
    ("get", "/api/v1/admin/catalog?site=sushi", None),
    ("get", "/api/v1/admin/leads.csv?site=dental", None),
    ("get", "/api/v1/admin/stats?site=dental", None),
    ("get", "/api/v1/admin/users", None),
    ("post", "/api/v1/admin/users", {"email": "x@x.ru", "name": "X", "password": "password123"}),
    ("patch", "/api/v1/admin/users/1", {"role": "staff"}),
    ("delete", "/api/v1/admin/users/1", None),
]


@pytest.mark.parametrize("role", ["staff", "admin"])
@pytest.mark.parametrize("method, path, body", FORBIDDEN, ids=[f"{m} {p}" for m, p, _ in FORBIDDEN])
def test_other_sites_are_forbidden(client, world, role, method, path, body):
    url = path.format(**world)
    kwargs = {"headers": world["users"][role]}
    if body is not None:
        kwargs["json"] = body
    assert getattr(client, method)(url, **kwargs).status_code == 403


@pytest.mark.parametrize("role", ["staff", "admin"])
def test_lists_contain_only_own_sites(client, world, role):
    h = world["users"][role]
    for kind in ("leads", "orders", "bookings"):
        assert client.get(f"/api/v1/admin/{kind}", headers=h).json()["total"] == 0
    assert client.get("/api/v1/admin/catalog", headers=h).json() == []
    stats = client.get("/api/v1/admin/stats", headers=h).json()
    assert stats["by_site"] == {} and stats["revenue"] == 0
    csv = client.get("/api/v1/admin/leads.csv", headers=h).text
    assert csv.count("\n") == 1  # только заголовок
