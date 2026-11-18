"""Публичные эндпоинты: их вызывают формы на сайтах. Авторизации нет, зато есть валидация, honeypot и лимит частоты."""

from datetime import date, datetime, time, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..deps import DB, get_site
from ..limits import rate_limit, read_limit
from ..models import Booking, CatalogItem, Lead, Order
from ..pricing import price_order
from ..schemas import BookingIn, CatalogOut, Created, LeadIn, OrderIn, OrderStatusOut
from ..services.booking import check_slot, local_time, reserve, slot_lock_key
from ..sites import Site

router = APIRouter(prefix="/api/v1/sites/{site}", tags=["public"])
SiteDep = Annotated[Site, Depends(get_site)]


def _feature(site: Site, flag: str) -> None:
    if not getattr(site, flag):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Этот сайт так не умеет")


def _spam(website: str) -> bool:
    return bool(website.strip())


@router.post("/leads", response_model=Created, status_code=201, dependencies=[Depends(rate_limit)])
def create_lead(site: SiteDep, body: LeadIn, db: DB):
    _feature(site, "leads")
    if not (body.phone or body.email):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Укажите телефон или e-mail")
    if _spam(body.website):
        return Created(id=0, status="new")  # боту отвечаем как обычно, но ничего не сохраняем
    lead = Lead(site=site.slug, **body.model_dump(exclude={"website"}))
    db.add(lead)
    db.commit()
    return Created(id=lead.id, status=lead.status)


@router.get("/slots", response_model=list[str], dependencies=[Depends(read_limit)])
def busy_slots(site: SiteDep, db: DB, resource: Annotated[str, Query(max_length=100)], day: Annotated[date, Query(alias="date")]):
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
    reserve(db, site, body.resource, starts_at)  # место занимается в той же транзакции, что и запись
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
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Укажите адрес доставки")
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


@router.get("/orders/{token}", response_model=OrderStatusOut, dependencies=[Depends(read_limit)])
def order_status(site: SiteDep, token: Annotated[str, Path(max_length=32)], db: DB):
    """Статус заказа для экрана отслеживания. Доступ по токену из ответа на заказ, а не по номеру."""
    order = db.scalar(select(Order).where(Order.token == token, Order.site == site.slug))
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Заказ не найден")
    return order


@router.get("/catalog", response_model=list[CatalogOut], dependencies=[Depends(read_limit)])
def public_catalog(site: SiteDep, db: DB):
    _feature(site, "catalog")
    return db.scalars(select(CatalogItem).where(CatalogItem.site == site.slug).order_by(CatalogItem.id)).all()
