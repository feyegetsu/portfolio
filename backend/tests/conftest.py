import os

# Настройки читаются при импорте приложения, поэтому задаём их до него
os.environ.update(
    DATABASE_URL="sqlite://",
    SECRET_KEY="test-secret",
    OWNER_EMAIL="owner@test.dev",
    OWNER_PASSWORD="owner-password",
    RATE_LIMIT="5",
)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.deps import rate_limit  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402

PHONE = "+7 (900) 123-45-67"


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    rate_limit.hits.clear()
    with TestClient(app) as c:
        yield c


def login(client: TestClient, email: str = "owner@test.dev", password: str = "owner-password") -> dict:
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def owner(client):
    return login(client)
