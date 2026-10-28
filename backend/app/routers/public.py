"""Публичные эндпоинты: их вызывают формы на сайтах. Авторизации нет, зато есть валидация, honeypot и лимит частоты."""

from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..deps import DB, get_site, rate_limit
from ..models import Booking, CatalogItem, Lead, Order
from ..schemas import BookingIn, CatalogOut, Created, LeadIn, OrderIn, OrderStatusOut
from ..sites import Site

router = APIRouter(prefix="/api/v1/sites/{site}", tags=["public"])
SiteDep = Annotated[Site, Depends(get_site)]


def _feature(site: Site, flag: str) -> None:
    if not getattr(site, flag):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Этот сайт так не умеет")


def _spam(website: str) -> bool:
    return bool(website.strip())


def _lock(site: Site, resource: str, starts_at: datetime) -> str | None:
    return f"{site.slug}|{resource}|{starts_at.isoformat()}" if site.exclusive_slots else None


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
    # Храним «настенное» время заведения; сравниваем с текущим временем в том же поясе
    now = datetime.now(body.starts_at.tzinfo).replace(tzinfo=None)
    starts_at = body.starts_at.replace(tzinfo=None, second=0, microsecond=0)
    if starts_at < now - timedelta(minutes=5):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Это время уже прошло")
    if _spam(body.website):
        return Created(id=0, status="confirmed")
    booking = Booking(
        site=site.slug, resource=body.resource, service=body.service, starts_at=starts_at,
        name=body.name, phone=body.phone, slot_lock=_lock(site, body.resource, starts_at),
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

    items = [i.model_dump() for i in body.items]
    if site.catalog:
        # Цены и наличие берём из каталога, а не из запроса: клиент не может подменить цену
        catalog = {c.ref: c for c in db.scalars(select(CatalogItem).where(CatalogItem.site == site.slug))}
        for item in items:
            known = catalog.get(item["ref"])
            if known and not known.active:
                raise HTTPException(status.HTTP_409_CONFLICT, f"«{known.name}» закончилось")
            if known:
                item["price"] = known.price

    order = Order(
        site=site.slug, items=items, total=sum(i["price"] * i["qty"] for i in items),
        name=body.name, phone=body.phone, address=body.address, mode=body.mode, comment=body.comment,
    )
    db.add(order)
    db.commit()
    return Created(id=order.id, status=order.status)


@router.get("/orders/{order_id}", response_model=OrderStatusOut)
def order_status(site: SiteDep, order_id: int, db: DB):
    """Статус заказа для экрана отслеживания."""
    order = db.get(Order, order_id)
    if not order or order.site != site.slug:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Заказ не найден")
    return order


@router.get("/catalog", response_model=list[CatalogOut])
def public_catalog(site: SiteDep, db: DB):
    _feature(site, "catalog")
    return db.scalars(select(CatalogItem).where(CatalogItem.site == site.slug).order_by(CatalogItem.id)).all()
