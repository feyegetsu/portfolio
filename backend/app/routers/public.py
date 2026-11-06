"""Публичные эндпоинты: их вызывают формы на сайтах. Авторизации нет, зато есть валидация, honeypot и лимит частоты."""

from datetime import date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import DB, get_site, rate_limit
from ..models import Booking, CatalogItem, Lead, Order
from ..pricing import price_order
from ..schemas import BookingIn, CatalogOut, Created, LeadIn, OrderIn, OrderStatusOut
from ..sites import Site

router = APIRouter(prefix="/api/v1/sites/{site}", tags=["public"])
SiteDep = Annotated[Site, Depends(get_site)]


def _feature(site: Site, flag: str) -> None:
    if not getattr(site, flag):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Этот сайт так не умеет")


def _spam(website: str) -> bool:
    return bool(website.strip())


def slot_lock_key(site: Site, resource: str, starts_at: datetime) -> str | None:
    return f"{site.slug}|{resource}|{starts_at.isoformat()}" if site.exclusive_slots else None


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
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Это время уже прошло")
    if starts_at > now + timedelta(days=site.horizon_days):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Запись открыта на {site.horizon_days} дней вперёд")
    if starts_at.minute % site.step_minutes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Выберите время из расписания")
    if not site.is_open(starts_at.hour * 60 + starts_at.minute):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "В это время мы закрыты")
    if site.resources is not None and resource not in site.resources:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Такого мастера или занятия нет")


def check_capacity(db: Session, site: Site, resource: str, starts_at: datetime, exclude_id: int | None = None) -> None:
    """Места на групповом занятии или столы в заведении. Эксклюзивные слоты держит уникальный ключ в БД."""
    capacity = site.resources.get(resource) if site.resources is not None else site.slot_capacity
    if not capacity:
        return
    query = select(func.count()).select_from(Booking).where(
        Booking.site == site.slug, Booking.starts_at == starts_at, Booking.status != "cancelled")
    if site.resources is not None:
        query = query.where(Booking.resource == resource)
    if exclude_id:
        query = query.where(Booking.id != exclude_id)
    if db.scalar(query) >= capacity:
        raise HTTPException(status.HTTP_409_CONFLICT, "На это время мест уже нет")


@router.post("/leads", response_model=Created, status_code=201, dependencies=[Depends(rate_limit)])
def create_lead(site: SiteDep, body: LeadIn, db: DB):
    _feature(site, "leads")
    if not (body.phone or body.email):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Укажите телефон или e-mail")
    if _spam(body.website):
        return Created(id=0, status="new")  # боту отвечаем как обычно, но ничего не сохраняем
    lead = Lead(site=site.slug, **body.model_dump(exclude={"website"}))
    db.add(lead)
    db.commit()
    return Created(id=lead.id, status=lead.status)


@router.get("/slots", response_model=list[str])
def busy_slots(site: SiteDep, db: DB, resource: str, day: Annotated[date, Query(alias="date")]):
    """Занятые слоты на день, чтобы форма записи сразу их заблокировала."""
    _feature(site, "bookings")
    start = datetime.combine(day, time.min)
    rows = db.scalars(
        select(Booking.starts_at).where(
            Booking.site == site.slug,
            Booking.resource == resource,
            Booking.status != "cancelled",
            Booking.starts_at >= start,
            Booking.starts_at < start + timedelta(days=1),
        )
    )
    return [t.strftime("%H:%M") for t in rows]


@router.post("/bookings", response_model=Created, status_code=201, dependencies=[Depends(rate_limit)])
def create_booking(site: SiteDep, body: BookingIn, db: DB):
    _feature(site, "bookings")
    # Храним «настенное» время заведения и сравниваем с текущим временем в его часовом поясе
    starts_at = local_time(site, body.starts_at)
    check_slot(site, body.resource, starts_at)
    if _spam(body.website):
        return Created(id=0, status="confirmed")
    check_capacity(db, site, body.resource, starts_at)
    booking = Booking(
        site=site.slug, resource=body.resource, service=body.service, starts_at=starts_at,
        name=body.name, phone=body.phone, slot_lock=slot_lock_key(site, body.resource, starts_at),
    )
    db.add(booking)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Это время уже заняли, выберите другое") from None
    return Created(id=booking.id, status=booking.status)


@router.post("/orders", response_model=Created, status_code=201, dependencies=[Depends(rate_limit)])
def create_order(site: SiteDep, body: OrderIn, db: DB):
    _feature(site, "orders")
    if body.mode == "delivery" and not body.address.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Укажите адрес доставки")
    if _spam(body.website):
        return Created(id=0, status="new")

    # Цены, доставку и промокод считает сервер по каталогу: из запроса берём только позиции и количество
    catalog = {c.ref: c for c in db.scalars(select(CatalogItem).where(CatalogItem.site == site.slug))}
    items = price_order(body.items, catalog, site.pricing, body.mode, body.promo)

    order = Order(
        site=site.slug, items=items, total=sum(i["price"] * i["qty"] for i in items),
        name=body.name, phone=body.phone, address=body.address, mode=body.mode, comment=body.comment,
    )
    db.add(order)
    db.commit()
    return Created(id=order.id, status=order.status, token=order.token)


@router.get("/orders/{token}", response_model=OrderStatusOut)
def order_status(site: SiteDep, token: str, db: DB):
    """Статус заказа для экрана отслеживания. Доступ по токену из ответа на заказ, а не по номеру."""
    order = db.scalar(select(Order).where(Order.token == token, Order.site == site.slug))
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Заказ не найден")
    return order


@router.get("/catalog", response_model=list[CatalogOut])
def public_catalog(site: SiteDep, db: DB):
    _feature(site, "catalog")
    return db.scalars(select(CatalogItem).where(CatalogItem.site == site.slug).order_by(CatalogItem.id)).all()
