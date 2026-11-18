"""BE-001: схему создают миграции Alembic, и она совпадает с моделями."""

from dataclasses import replace

import pytest
from alembic.autogenerate import compare_metadata
from alembic.runtime.migration import MigrationContext
from sqlalchemy import inspect, text

from app import migrate
from app.config import check_secrets, settings
from app.db import Base, make_engine


@pytest.fixture
def engine(tmp_path):
    e = make_engine(f"sqlite:///{(tmp_path / 'm.db').as_posix()}")
    yield e
    e.dispose()


def test_upgrade_creates_schema_matching_models(engine):
    assert migrate.upgrade(engine) == migrate.head()
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
    assert diff == [], f"Модели и миграции расходятся, нужна новая миграция: {diff}"
    assert migrate.is_up_to_date(engine)


def test_upgrade_is_idempotent(engine):
    migrate.upgrade(engine)
    assert migrate.upgrade(engine) == migrate.head()


def test_legacy_database_is_stamped_and_upgraded(engine):
    # База, созданная create_all до появления миграций: схема базовой ревизии, отметки Alembic нет
    migrate.upgrade(engine, migrate.BASELINE)
    with engine.begin() as conn:
        conn.execute(text("insert into users (email, name, password_hash, role, created_at) "
                          "values ('a@b.ru', 'A', 'x', 'owner', '2026-01-01')"))
        conn.execute(text("drop table alembic_version"))
    assert migrate.upgrade(engine) == migrate.head()
    with engine.connect() as conn:
        assert conn.execute(text("select email from users")).scalar() == "a@b.ru"  # данные на месте


def test_empty_database_is_not_up_to_date(engine):
    assert not migrate.is_up_to_date(engine)
    assert "users" not in inspect(engine).get_table_names()


def test_sqlite_refused_in_production():
    prod = replace(settings, env="production", database_url="sqlite:///./portfolio.db", allow_sqlite=False,
                   password_iterations=600_000)
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        check_secrets(prod)
    check_secrets(replace(prod, allow_sqlite=True))
    check_secrets(replace(prod, database_url="postgresql+psycopg://u:p@h/db"))


def test_sqlite_tables_get_autoincrement_on_upgrade(engine):
    # SEC-002: старые таблицы SQLite пересоздаются с AUTOINCREMENT, индексы и данные сохраняются
    migrate.upgrade(engine, migrate.BASELINE)
    with engine.begin() as conn:
        conn.execute(text("insert into catalog (site, ref, name, category, price, active) values ('sushi', 's1', 'Сет', '', 1, 1)"))
    migrate.upgrade(engine)
    with engine.connect() as conn:
        ddl = {n: s for n, s in conn.execute(text("select name, sql from sqlite_master where type = 'table'"))}
        assert conn.execute(text("select name from catalog")).scalar() == "Сет"
        indexes = {i["name"] for i in inspect(conn).get_indexes("catalog")}
    for table in ("users", "leads", "bookings", "orders", "catalog"):
        assert "AUTOINCREMENT" in ddl[table], table
    assert "ix_catalog_site" in indexes
