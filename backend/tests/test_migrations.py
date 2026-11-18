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


def test_existing_bookings_fill_slot_counters(engine):
    # BUG-001: при переходе на счётчик уже занятые места учитываются
    migrate.upgrade(engine, "0002")
    rows = [("restaurant", "Стол на 2", "confirmed"), ("restaurant", "Стол на 4", "confirmed"),
            ("restaurant", "Стол на 2", "cancelled"), ("fitness", "Кроссфит", "confirmed"),
            ("fitness", "Кроссфит", "done"), ("barbershop", "Артём", "confirmed")]
    with engine.begin() as conn:
        for site, resource, status in rows:
            conn.execute(text("insert into bookings (site, resource, service, starts_at, name, phone, status, created_at) "
                              "values (:s, :r, '', '2026-12-01 20:00:00', 'A', '+79001234567', :st, '2026-11-01')"),
                         {"s": site, "r": resource, "st": status})
    migrate.upgrade(engine)
    with engine.connect() as conn:
        counters = {(s, k): n for s, k, n in conn.execute(text("select site, resource_key, taken from slot_counters"))}
    assert counters == {("restaurant", ""): 2, ("fitness", "Кроссфит"): 2}


def test_sites_with_catalog_are_marked_as_seeded(engine):
    # BUG-003: каталог, который уже заливался, не зальётся повторно после перехода на отметки
    migrate.upgrade(engine, "0003")
    with engine.begin() as conn:
        conn.execute(text("insert into catalog (site, ref, name, category, price, active) values ('sushi', 's1', 'Сет', '', 1, 1)"))
    migrate.upgrade(engine)
    with engine.connect() as conn:
        assert conn.execute(text("select key from seed_marks")).scalars().all() == ["catalog:sushi"]


def test_existing_leads_get_search_text(engine):
    migrate.upgrade(engine, "0004")
    with engine.begin() as conn:
        conn.execute(text("insert into leads (site, kind, name, phone, email, message, data, status, created_at) "
                          "values ('cafe', 'table', 'Анна', '+79001234567', '', 'У ОКНА', '{}', 'new', '2026-11-01')"))
    migrate.upgrade(engine)
    with engine.connect() as conn:
        assert conn.execute(text("select search_text from leads")).scalar() == "анна +79001234567 у окна"
