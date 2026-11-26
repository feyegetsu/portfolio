"""Окружение Alembic: схема — app.models, адрес базы — DATABASE_URL.

Код приложения может передать готовое соединение через config.attributes["connection"] (app/migrate.py, тесты).
"""

from logging.config import fileConfig

from alembic import context

from app import models  # noqa: F401 — регистрирует таблицы в Base.metadata
from app.config import settings
from app.db import Base, make_engine

config = context.config
target_metadata = Base.metadata

if config.config_file_name and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)


def _configure(**kwargs) -> None:
    context.configure(target_metadata=target_metadata, compare_type=True, **kwargs)


def run_offline() -> None:
    _configure(url=settings.database_url, literal_binds=True, dialect_opts={"paramstyle": "named"},
               render_as_batch=settings.database_url.startswith("sqlite"))
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    connection = config.attributes.get("connection")
    if connection is None:
        with make_engine(settings.database_url).connect() as conn:
            _run(conn)
            conn.commit()
    else:
        _run(connection)


def _run(connection) -> None:
    # SQLite не умеет большинство ALTER TABLE: batch-режим пересоздаёт таблицу с новой схемой
    _configure(connection=connection, render_as_batch=connection.dialect.name == "sqlite")
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_offline()
else:
    run_online()
