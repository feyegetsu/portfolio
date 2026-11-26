from collections.abc import Iterator
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import settings


def utcnow() -> datetime:
    """Время в UTC без tzinfo: одинаково хранится в SQLite и PostgreSQL."""
    return datetime.now(UTC).replace(tzinfo=None)


def to_local(dt: datetime, tz: str) -> datetime:
    """Время из базы (UTC без tzinfo) в «настенное» время часового пояса tz, тоже без tzinfo."""
    return dt.replace(tzinfo=UTC).astimezone(ZoneInfo(tz)).replace(tzinfo=None)


def from_local(dt: datetime, tz: str) -> datetime:
    """Обратно: «настенное» время пояса tz в UTC без tzinfo, как хранится в базе."""
    return dt.replace(tzinfo=ZoneInfo(tz)).astimezone(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    if url.startswith("sqlite"):
        kwargs = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool  # одна общая БД в памяти для тестов
        return create_engine(url, **kwargs)
    return create_engine(url, pool_pre_ping=True)


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
