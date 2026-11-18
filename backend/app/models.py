import secrets
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, utcnow


# SQLite без AUTOINCREMENT отдаёт освободившийся максимальный id новой строке: токен удалённого
# пользователя достался бы новому. С AUTOINCREMENT id не переиспользуются (в PostgreSQL так и так)
NO_ID_REUSE = {"sqlite_autoincrement": True}


class User(Base):
    __tablename__ = "users"
    __table_args__ = NO_ID_REUSE

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))  # owner | admin | staff
    # None — доступ ко всем сайтам, иначе список slug
    sites: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    # Растёт при выходе, смене пароля, роли или сайтов: выданные раньше токены перестают действовать
    token_version: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Lead(Base):
    """Заявка с формы: бронь столика, консультация, просмотр квартиры, подписка."""

    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_site_created", "site", "created_at"), NO_ID_REUSE)

    id: Mapped[int] = mapped_column(primary_key=True)
    site: Mapped[str] = mapped_column(String(40), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(100), default="")
    phone: Mapped[str] = mapped_column(String(30), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    message: Mapped[str] = mapped_column(Text, default="")
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Booking(Base):
    """Запись на время. Эксклюзивный слот держит уникальный slot_lock, места на занятиях и столы — SlotCounter."""

    __tablename__ = "bookings"
    __table_args__ = NO_ID_REUSE

    id: Mapped[int] = mapped_column(primary_key=True)
    site: Mapped[str] = mapped_column(String(40), index=True)
    resource: Mapped[str] = mapped_column(String(100))  # мастер или занятие
    service: Mapped[str] = mapped_column(String(100), default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    slot_lock: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SlotCounter(Base):
    """Сколько мест занято на время: по занятию (resource_key — его название) или по заведению (resource_key пуст).

    Строка обновляется атомарно (services/booking.py), поэтому вместимость не превышается и при одновременных запросах.
    """

    __tablename__ = "slot_counters"
    __table_args__ = (UniqueConstraint("site", "resource_key", "starts_at", name="uq_slot_counters_slot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    site: Mapped[str] = mapped_column(String(40))
    resource_key: Mapped[str] = mapped_column(String(100), default="")
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    taken: Mapped[int] = mapped_column(Integer, default=0)


def _order_token() -> str:
    return secrets.token_urlsafe(16)


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = NO_ID_REUSE

    id: Mapped[int] = mapped_column(primary_key=True)
    # Отслеживание заказа идёт по случайному токену: по порядковому id чужие заказы не перебрать
    token: Mapped[str] = mapped_column(String(32), unique=True, index=True, default=_order_token)
    site: Mapped[str] = mapped_column(String(40), index=True)
    items: Mapped[list] = mapped_column(JSON, default=list)
    total: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(30))
    address: Mapped[str] = mapped_column(String(300), default="")
    mode: Mapped[str] = mapped_column(String(20), default="delivery")
    comment: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SeedMark(Base):
    """Отметка, что начальные данные уже заливались (например, «catalog:sushi»): удалённое владельцем не вернётся."""

    __tablename__ = "seed_marks"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)


class CatalogItem(Base):
    """Позиция каталога. ref — внешний id позиции на сайте, по нему сайт применяет цену и стоп-лист."""

    __tablename__ = "catalog"
    __table_args__ = (UniqueConstraint("site", "ref", name="uq_catalog_site_ref"), NO_ID_REUSE)

    id: Mapped[int] = mapped_column(primary_key=True)
    site: Mapped[str] = mapped_column(String(40), index=True)
    ref: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(60), default="")
    price: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
