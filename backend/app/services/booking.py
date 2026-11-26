"""Правила записи на время и учёт мест.

Эксклюзивный слот (мастер барбершопа) держит уникальный ключ bookings.slot_lock. Места на занятии
и столы в заведении считает таблица slot_counters: занять место — один атомарный оператор
INSERT … ON CONFLICT DO UPDATE SET taken = taken + 1 WHERE taken < вместимость. Два одновременных
запроса не могут оба увидеть «осталось одно место»: проверка и запись происходят в одной строке БД.
"""

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.orm import Session

from ..models import Booking, SlotCounter
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
    if site.opening_day(starts_at) is None:
        msg = "В этот день мы закрыты" if site.closed_all_day(starts_at) else "В это время мы закрыты"
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, msg)
    if site.resources is not None and resource not in site.resources:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Такого мастера или занятия нет")


def day_slots(site: Site, day: date) -> list[datetime]:
    """Все слоты записи дня открытия day, включая ночные после полуночи (как daySlots в api.js)."""
    schedule = site.schedule if site.schedule is not None else dict.fromkeys(range(7), site.hours)
    hours = schedule.get(day.weekday())
    if not hours:
        return []
    start, end = hours[0] * 60, (hours[1] if hours[0] < hours[1] else hours[1] + 24) * 60
    base = datetime.combine(day, time.min)
    return [base + timedelta(minutes=m) for m in range(start, end, site.step_minutes)]


def availability(db: Session, site: Site, day: date, resource: str | None) -> list[dict]:
    """Свободные места по слотам дня: по счётчику мест, у мастера — 1 или 0. left=None — ограничения нет."""
    if site.resources is not None and resource not in site.resources:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Такого мастера или занятия нет")
    slots = day_slots(site, day)
    if not slots:
        return []
    window = (SlotCounter.starts_at >= slots[0], SlotCounter.starts_at <= slots[-1])
    cap = capacity(site, resource or "")
    if cap:
        taken = dict(db.execute(select(SlotCounter.starts_at, SlotCounter.taken)
                                .where(SlotCounter.site == site.slug, SlotCounter.resource_key == cap[0], *window)).all())
        left = {t: max(0, cap[1] - taken.get(t, 0)) for t in slots}
    elif site.exclusive_slots:
        busy = set(db.scalars(select(Booking.starts_at).where(
            Booking.site == site.slug, Booking.resource == resource, Booking.status != "cancelled",
            Booking.starts_at >= slots[0], Booking.starts_at <= slots[-1])))
        left = {t: 0 if t in busy else 1 for t in slots}
    else:
        left = dict.fromkeys(slots)
    return [{"time": t.strftime("%H:%M"), "starts_at": t.isoformat(), "left": left[t]} for t in slots]


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
    table = SlotCounter.__table__
    stmt = _insert(db)(table).values(site=site.slug, resource_key=key, starts_at=starts_at, taken=1)
    stmt = stmt.on_conflict_do_update(
        index_elements=["site", "resource_key", "starts_at"],
        set_={"taken": table.c.taken + 1},
        where=table.c.taken < limit,
    ).returning(table.c.taken)
    # Место занято, только если оператор вернул строку. rowcount у INSERT … ON CONFLICT ненадёжен: insert по
    # ORM-сущности SQLAlchemy выполняет своим путём, и в PostgreSQL отказ по WHERE не давал 0 — мест не хватало
    if db.execute(stmt).first() is None:
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
