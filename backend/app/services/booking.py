"""Правила записи на время и учёт мест.

Эксклюзивный слот (мастер барбершопа) держит уникальный ключ bookings.slot_lock. Места на занятии
и столы в заведении считает таблица slot_counters: занять место — один атомарный оператор
INSERT … ON CONFLICT DO UPDATE SET taken = taken + 1 WHERE taken < вместимость. Два одновременных
запроса не могут оба увидеть «осталось одно место»: проверка и запись происходят в одной строке БД.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from ..models import SlotCounter
from ..sites import Site

FULL = "На это время мест уже нет"


def site_now(site: Site) -> datetime:
    """Текущее «настенное» время заведения: сервер может жить в UTC, а запись идёт по местному времени."""
    return datetime.now(ZoneInfo(site.tz)).replace(tzinfo=None)


def local_time(site: Site, value: datetime) -> datetime:
    """Время из запроса в часовом поясе заведения, без секунд. Время без пояса считаем уже местным."""
    if value.tzinfo:
        value = value.astimezone(ZoneInfo(site.tz))
    return value.replace(tzinfo=None, second=0, microsecond=0)


def check_slot(site: Site, resource: str, starts_at: datetime) -> None:
    """Правила записи: не в прошлом, не дальше горизонта, по сетке, в часы работы, к существующему ресурсу."""
    now = site_now(site)
    if starts_at < now - timedelta(minutes=5):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Это время уже прошло")
    if starts_at > now + timedelta(days=site.horizon_days):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Запись открыта на {site.horizon_days} дней вперёд")
    if starts_at.minute % site.step_minutes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Выберите время из расписания")
    if not site.is_open(starts_at.hour * 60 + starts_at.minute):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "В это время мы закрыты")
    if site.resources is not None and resource not in site.resources:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Такого мастера или занятия нет")


def slot_lock_key(site: Site, resource: str, starts_at: datetime) -> str | None:
    return f"{site.slug}|{resource}|{starts_at.isoformat()}" if site.exclusive_slots else None


def capacity(site: Site, resource: str) -> tuple[str, int] | None:
    """(ключ счётчика, вместимость): места на занятии считаются по занятию, столы — по всему заведению."""
    if site.resources is not None:
        cap = site.resources.get(resource)
        return (resource, cap) if cap else None
    return ("", site.slot_capacity) if site.slot_capacity else None


def _insert(db: Session):
    return (postgresql if db.get_bind().dialect.name == "postgresql" else sqlite).insert


def reserve(db: Session, site: Site, resource: str, starts_at: datetime) -> None:
    """Занимает место в той же транзакции, что и запись; при полном слоте — 409. Эксклюзивные слоты не трогает."""
    cap = capacity(site, resource)
    if not cap:
        return
    key, limit = cap
    stmt = _insert(db)(SlotCounter).values(site=site.slug, resource_key=key, starts_at=starts_at, taken=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=["site", "resource_key", "starts_at"],
        set_={"taken": SlotCounter.taken + 1},
        where=SlotCounter.taken < limit,
    )
    if db.execute(stmt).rowcount == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, FULL)


def release(db: Session, site: Site, resource: str, starts_at: datetime) -> None:
    """Освобождает место при отмене записи."""
    cap = capacity(site, resource)
    if not cap:
        return
    db.execute(
        update(SlotCounter)
        .where(SlotCounter.site == site.slug, SlotCounter.resource_key == cap[0], SlotCounter.starts_at == starts_at,
               SlotCounter.taken > 0)
        .values(taken=SlotCounter.taken - 1)
    )
