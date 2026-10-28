"""Админка: заявки, записи, заказы, каталог, статистика и команда. Каждый запрос ограничен сайтами пользователя."""

import csv
import io
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from ..db import utcnow
from ..deps import DB, CurrentUser, allowed_sites, check_site_access, require
from ..models import Booking, CatalogItem, Lead, Order, User
from ..schemas import (
    BookingOut,
    BookingPatch,
    CatalogIn,
    CatalogOut,
    CatalogPatch,
    LeadOut,
    LeadPatch,
    OrderOut,
    OrderPatch,
    Page,
    Stats,
    UserIn,
    UserOut,
)
from ..security import hash_password
from ..sites import SITES

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0)]


def _scope(model, user: User, site: str | None):
    """Базовый запрос с учётом доступных пользователю сайтов и фильтра по сайту."""
    sites = allowed_sites(user)
    if site:
        check_site_access(user, site)
        sites = [site]
    return select(model).where(model.site.in_(sites))


def _page(db, query, model, limit: int, offset: int):
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(model.created_at.desc(), model.id.desc()).limit(limit).offset(offset)).all()
    return {"items": items, "total": total}


def _get_owned(db, model, obj_id: int, user: User):
    obj = db.get(model, obj_id)
    if not obj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Не найдено")
    check_site_access(user, obj.site)
    return obj


# ---------- Заявки ----------

@router.get("/leads", response_model=Page[LeadOut])
def list_leads(user: CurrentUser, db: DB, site: str | None = None, status_: Annotated[str | None, Query(alias="status")] = None,
               q: str | None = None, limit: Limit = 50, offset: Offset = 0):
    query = _scope(Lead, user, site)
    if status_:
        query = query.where(Lead.status == status_)
    if q:
        like = f"%{q.strip()}%"
        query = query.where(or_(Lead.name.ilike(like), Lead.phone.ilike(like), Lead.email.ilike(like), Lead.message.ilike(like)))
    return _page(db, query, Lead, limit, offset)


@router.patch("/leads/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, body: LeadPatch, user: CurrentUser, db: DB):
    lead = _get_owned(db, Lead, lead_id, user)
    lead.status = body.status
    db.commit()
    return lead


@router.get("/leads.csv")
def export_leads(user: CurrentUser, db: DB, site: str | None = None):
    """Выгрузка заявок для Excel: UTF-8 с BOM и точкой с запятой, чтобы русский текст открывался без танцев."""
    rows = db.scalars(_scope(Lead, user, site).order_by(Lead.created_at.desc())).all()
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["id", "Дата", "Сайт", "Тип", "Имя", "Телефон", "E-mail", "Комментарий", "Статус"])
    for r in rows:
        writer.writerow([r.id, r.created_at.strftime("%d.%m.%Y %H:%M"), SITES[r.site].name, r.kind, r.name, r.phone, r.email, r.message, r.status])
    return Response("﻿" + buf.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="leads.csv"'})


# ---------- Записи ----------

@router.get("/bookings", response_model=Page[BookingOut])
def list_bookings(user: CurrentUser, db: DB, site: str | None = None, upcoming: bool = False,
                  limit: Limit = 50, offset: Offset = 0):
    query = _scope(Booking, user, site)
    if upcoming:
        query = query.where(Booking.starts_at >= utcnow() - timedelta(hours=12), Booking.status == "confirmed")
    return _page(db, query, Booking, limit, offset)


@router.patch("/bookings/{booking_id}", response_model=BookingOut)
def update_booking(booking_id: int, body: BookingPatch, user: CurrentUser, db: DB):
    booking = _get_owned(db, Booking, booking_id, user)
    booking.status = body.status
    if body.status == "cancelled":
        booking.slot_lock = None  # отмена освобождает слот
    db.commit()
    return booking


# ---------- Заказы ----------

@router.get("/orders", response_model=Page[OrderOut])
def list_orders(user: CurrentUser, db: DB, site: str | None = None, status_: Annotated[str | None, Query(alias="status")] = None,
                limit: Limit = 50, offset: Offset = 0):
    query = _scope(Order, user, site)
    if status_:
        query = query.where(Order.status == status_)
    return _page(db, query, Order, limit, offset)


@router.patch("/orders/{order_id}", response_model=OrderOut)
def update_order(order_id: int, body: OrderPatch, user: CurrentUser, db: DB):
    order = _get_owned(db, Order, order_id, user)
    order.status = body.status
    db.commit()
    return order


# ---------- Каталог (admin и выше) ----------

@router.get("/catalog", response_model=list[CatalogOut])
def list_catalog(user: CurrentUser, db: DB, site: str | None = None):
    return db.scalars(_scope(CatalogItem, user, site).order_by(CatalogItem.site, CatalogItem.id)).all()


@router.post("/catalog/{site}", response_model=CatalogOut, status_code=201, dependencies=[Depends(require("admin"))])
def add_catalog_item(site: str, body: CatalogIn, user: CurrentUser, db: DB):
    check_site_access(user, site)
    if site not in SITES or not SITES[site].catalog:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "У сайта нет каталога")
    item = CatalogItem(site=site, **body.model_dump())
    db.add(item)
    db.commit()
    return item


@router.patch("/catalog/item/{item_id}", response_model=CatalogOut, dependencies=[Depends(require("admin"))])
def update_catalog_item(item_id: int, body: CatalogPatch, user: CurrentUser, db: DB):
    item = _get_owned(db, CatalogItem, item_id, user)
    for key, value in body.model_dump(exclude_none=True).items():
        setattr(item, key, value)
    db.commit()
    return item


@router.delete("/catalog/item/{item_id}", status_code=204, dependencies=[Depends(require("admin"))])
def delete_catalog_item(item_id: int, user: CurrentUser, db: DB):
    db.delete(_get_owned(db, CatalogItem, item_id, user))
    db.commit()


# ---------- Статистика ----------

@router.get("/stats", response_model=Stats)
def stats(user: CurrentUser, db: DB, site: str | None = None, days: Annotated[int, Query(ge=1, le=90)] = 14):
    leads = _scope(Lead, user, site).subquery()
    bookings = _scope(Booking, user, site).subquery()
    orders = _scope(Order, user, site).subquery()
    count = lambda sq, *where: db.scalar(select(func.count()).select_from(sq).where(*where))  # noqa: E731

    since = (utcnow() - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    by_day = {(since + timedelta(days=i)).date().isoformat(): 0 for i in range(days)}
    for sq in (leads, bookings, orders):
        for (created,) in db.execute(select(sq.c.created_at).where(sq.c.created_at >= since)):
            key = created.date().isoformat()
            if key in by_day:
                by_day[key] += 1

    by_site: dict[str, int] = {}
    for sq in (leads, bookings, orders):
        for slug, n in db.execute(select(sq.c.site, func.count()).group_by(sq.c.site)):
            by_site[slug] = by_site.get(slug, 0) + n

    return Stats(
        leads=count(leads),
        bookings=count(bookings),
        orders=count(orders),
        revenue=db.scalar(select(func.coalesce(func.sum(orders.c.total), 0)).where(orders.c.status != "cancelled")),
        new_leads=count(leads, leads.c.status == "new"),
        by_day=[{"date": d, "count": n} for d, n in by_day.items()],
        by_site=by_site,
    )


# ---------- Команда (только владелец) ----------

@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require("owner"))])
def list_users(db: DB):
    return db.scalars(select(User).order_by(User.id)).all()


@router.post("/users", response_model=UserOut, status_code=201, dependencies=[Depends(require("owner"))])
def add_user(body: UserIn, db: DB):
    if body.sites is not None and any(s not in SITES for s in body.sites):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Неизвестный сайт")
    user = User(email=body.email.lower().strip(), name=body.name, role=body.role, sites=body.sites,
                password_hash=hash_password(body.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Пользователь с таким e-mail уже есть") from None
    return user


@router.delete("/users/{user_id}", status_code=204)
def remove_user(user_id: int, owner: Annotated[User, Depends(require("owner"))], db: DB):
    if user_id == owner.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Нельзя удалить самого себя")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Не найдено")
    db.delete(user)
    db.commit()
