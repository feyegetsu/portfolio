"""SEC-002: токен привязан к версии пользователя, его можно погасить, а id удалённого пользователя не переиспользуется."""

import jwt
from conftest import login
from sqlalchemy import text

from app.config import settings
from app.db import engine

ME = "/api/v1/auth/me"


def add_user(client, owner, email, role="staff", password="password123"):
    r = client.post("/api/v1/admin/users", headers=owner,
                    json={"email": email, "name": email[0].upper(), "password": password, "role": role})
    assert r.status_code == 201, r.text
    return r.json()


def test_deleted_users_token_does_not_pass_to_new_user(client, owner):
    a = add_user(client, owner, "a@test.dev")
    token_a = login(client, "a@test.dev", "password123")
    assert client.get(ME, headers=token_a).json()["email"] == "a@test.dev"

    assert client.delete(f"/api/v1/admin/users/{a['id']}", headers=owner).status_code == 204
    assert client.get(ME, headers=token_a).status_code == 401

    b = add_user(client, owner, "b@test.dev", role="owner")
    assert b["id"] != a["id"], "id удалённого пользователя достался новому"
    assert client.get(ME, headers=token_a).status_code == 401


def test_sqlite_tables_do_not_reuse_ids():
    with engine.connect() as conn:
        ddl = conn.execute(text("select sql from sqlite_master where name = 'users'")).scalar()
    assert "AUTOINCREMENT" in ddl


def test_logout_revokes_token(client, owner):
    assert client.post("/api/v1/auth/logout", headers=owner).status_code == 204
    assert client.get(ME, headers=owner).status_code == 401
    assert client.get(ME, headers=login(client)).status_code == 200  # новый вход работает


def test_password_change_revokes_old_tokens(client, owner):
    add_user(client, owner, "c@test.dev")
    first, second = login(client, "c@test.dev", "password123"), login(client, "c@test.dev", "password123")
    r = client.post("/api/v1/auth/password", headers=first,
                    json={"current_password": "password123", "new_password": "new-password-1"})
    assert r.status_code == 200
    fresh = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert client.get(ME, headers=first).status_code == 401
    assert client.get(ME, headers=second).status_code == 401
    assert client.get(ME, headers=fresh).status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": "c@test.dev", "password": "password123"}).status_code == 401
    login(client, "c@test.dev", "new-password-1")


def test_password_change_needs_current_password(client, owner):
    r = client.post("/api/v1/auth/password", headers=owner, json={"current_password": "wrong", "new_password": "new-password-1"})
    assert r.status_code == 403
    assert client.get(ME, headers=owner).status_code == 200


def test_token_without_version_rejected(client, owner):
    me = client.get(ME, headers=owner).json()
    legacy = jwt.encode({"sub": str(me["id"]), "exp": 9_999_999_999}, settings.secret_key, algorithm="HS256")
    assert client.get(ME, headers={"Authorization": f"Bearer {legacy}"}).status_code == 401


def test_default_token_ttl_is_two_hours():
    assert settings.token_ttl_minutes == 120  # в тестах TOKEN_TTL_MINUTES не задан: это значение по умолчанию
