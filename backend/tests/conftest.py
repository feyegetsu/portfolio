import os

# Настройки читаются при импорте приложения, поэтому задаём их до него
os.environ.update(
    DATABASE_URL="sqlite://",
    SECRET_KEY="test-secret-key-that-is-long-enough-1234567890",
    OWNER_EMAIL="owner@test.dev",
    OWNER_PASSWORD="owner-password",
    RATE_LIMIT="5",
    ALLOW_SQLITE="1",
    ENV="test",
    # Быстрые хеши паролей: 600 000 итераций замедлили бы каждый вход в тестах в десятки раз
    PASSWORD_ITERATIONS="1000",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.deps import LOGIN_LIMITS, rate_limit  # noqa: E402
from app.main import app  # noqa: E402
from app.migrate import stamp_head  # noqa: E402
from app.seed import seed  # noqa: E402

PHONE = "+7 (900) 123-45-67"

# Для скорости схему в тестах создаёт create_all; что миграции дают ту же схему, проверяет test_migrations.py
Base.metadata.create_all(engine)
stamp_head(engine)


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    rate_limit.clear()
    for limiter in LOGIN_LIMITS:
        limiter.clear()
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str = "owner@test.dev", password: str = "owner-password") -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def owner(client):
    return login(client)
