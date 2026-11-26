"""Схема базы через миграции Alembic.

    python -m app.migrate        обновить схему до последней версии

Docker-образ делает это при каждом старте, до запуска API. Базу, созданную до появления миграций
(таблицы уже есть, а отметки Alembic нет), помечаем базовой ревизией и обновляем дальше,
поэтому ручной `alembic stamp` не нужен.
"""

import functools
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, Engine, inspect

BACKEND = Path(__file__).resolve().parents[1]
BASELINE = "0001"


def alembic_config(connection: Connection | None = None) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    if connection is not None:
        cfg.attributes["connection"] = connection
        cfg.attributes["configure_logger"] = False
    return cfg


@functools.cache
def head() -> str:
    return ScriptDirectory.from_config(alembic_config()).get_current_head()


def current(connection: Connection) -> str | None:
    return MigrationContext.configure(connection).get_current_revision()


def upgrade(engine: Engine, target: str = "head") -> str | None:
    with engine.begin() as conn:
        cfg = alembic_config(conn)
        if current(conn) is None and "users" in inspect(conn).get_table_names():
            command.stamp(cfg, BASELINE)
        command.upgrade(cfg, target)
        return current(conn)


def stamp_head(engine: Engine) -> None:
    """Для тестов: схема создана create_all по моделям, отмечаем её последней ревизией."""
    with engine.begin() as conn:
        command.stamp(alembic_config(conn), "head")


def is_up_to_date(engine: Engine) -> bool:
    with engine.connect() as conn:
        return current(conn) == head()


def main() -> int:
    from .config import check_secrets, settings

    check_secrets(settings)  # до подключения к базе: понятное сообщение вместо ошибки драйвера
    from .db import engine

    print("Схема базы на ревизии", upgrade(engine))
    return 0


if __name__ == "__main__":
    sys.exit(main())
