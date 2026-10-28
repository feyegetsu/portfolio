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
        "items": [{"name": "Букет", "qty": 2, "price": 1500}], "name": "Иван", "phone": PHONE, "mode": "pickup",
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
