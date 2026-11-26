"""Схемы запросов и ответов. Всё, что приходит с публичных форм, валидируется здесь."""

import json
import re
from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

PHONE_RE = re.compile(r"^\+?\d{10,15}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
DATA_MAX_CHARS = 4000  # доп. поля заявки: этого хватает любой форме с запасом
# Предельные длины полей публичных форм. Копию получает демо-движок (rules_export → LIMITS в api.js)
LIMITS = {
    "kind": 40, "name": 100, "email": 200, "message": 2000, "data": DATA_MAX_CHARS,
    "resource": 100, "service": 100,
    "items": 50, "ref": 60, "item_name": 200, "address": 300, "comment": 1000, "promo": 30,
    "catalog_name": 200,
}
T = TypeVar("T")

# Пробелы по краям обрезаются до проверки длины: имя из одних пробелов — пустое имя
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=LIMITS["name"])]
Text = Annotated[str, StringConstraints(strip_whitespace=True)]
LeadStatus = Literal["new", "in_progress", "done", "cancelled"]
BookingStatus = Literal["confirmed", "done", "cancelled"]
OrderStatus = Literal["new", "cooking", "delivering", "done", "cancelled"]
Role = Literal["owner", "admin", "staff"]


def normalize_phone(value: str) -> str:
    """Оставляем цифры и ведущий плюс: «+7 (900) 000-00-00» → «+79000000000»."""
    cleaned = re.sub(r"[^\d+]", "", value or "")
    if not PHONE_RE.match(cleaned):
        raise ValueError("Некорректный номер телефона")
    return cleaned


class Input(BaseModel):
    """Все входные схемы: неизвестное поле — 422, а не тихая потеря данных из-за опечатки (phon вместо phone)."""

    model_config = ConfigDict(extra="forbid")


class Honeypot(Input):
    # Скрытое поле: люди его не видят и не заполняют, а спам-боты заполняют
    website: str = ""


# ---------- Публичные формы ----------

class LeadIn(Honeypot):
    kind: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=LIMITS["kind"])]
    name: Text = Field("", max_length=LIMITS["name"])
    phone: str = ""
    email: str = Field("", max_length=LIMITS["email"])
    message: str = Field("", max_length=LIMITS["message"])
    data: dict = Field(default_factory=dict)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_phone(v) if v else v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip()
        if v and not EMAIL_RE.match(v):
            raise ValueError("Некорректный e-mail")
        return v.lower()

    @field_validator("data")
    @classmethod
    def _data(cls, v: dict) -> dict:
        if len(json.dumps(v, ensure_ascii=False)) > DATA_MAX_CHARS:
            raise ValueError("Слишком много данных в заявке")
        return v


class BookingIn(Honeypot):
    resource: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=LIMITS["resource"])]
    service: Text = Field("", max_length=LIMITS["service"])
    starts_at: datetime
    name: Name
    phone: str

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_phone(v)


class OrderItem(Input):
    ref: Annotated[str, Field(min_length=1, max_length=LIMITS["ref"])]
    name: str = Field("", max_length=LIMITS["item_name"])
    qty: Annotated[int, Field(ge=1, le=99)]
    # Цену браузер может прислать для наглядности, но сервер её не использует: считает по каталогу
    price: int = Field(0, ge=0, le=1_000_000)


class OrderIn(Honeypot):
    items: Annotated[list[OrderItem], Field(min_length=1, max_length=LIMITS["items"])]
    name: Name
    phone: str
    address: Text = Field("", max_length=LIMITS["address"])
    mode: Literal["delivery", "pickup"] = "delivery"
    comment: str = Field("", max_length=LIMITS["comment"])
    promo: str = Field("", max_length=LIMITS["promo"])

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_phone(v)


# ---------- Ответы ----------

class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LeadOut(ORM):
    id: int
    site: str
    kind: str
    name: str
    phone: str
    email: str
    message: str
    data: dict
    status: str
    created_at: datetime


class BookingOut(ORM):
    id: int
    site: str
    resource: str
    service: str
    starts_at: datetime
    name: str
    phone: str
    status: str
    created_at: datetime


class OrderOut(ORM):
    id: int
    site: str
    items: list[dict]
    total: int
    name: str
    phone: str
    address: str
    mode: str
    comment: str
    status: str
    created_at: datetime


class OrderStatusOut(ORM):
    id: int
    status: str
    total: int
    items: list[dict]


class SlotOut(BaseModel):
    time: str           # «19:30» — как на кнопке
    starts_at: str      # «2026-11-24T19:30:00» — что отправить в запись (ночные слоты — уже следующей датой)
    left: int | None    # свободных мест; None — без ограничения


class CatalogOut(ORM):
    id: int
    site: str
    ref: str
    name: str
    category: str
    price: int
    active: bool


class Created(BaseModel):
    id: int
    status: str
    # Секретный токен для отслеживания заказа: по порядковому номеру чужой заказ не посмотреть
    token: str | None = None


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int


# ---------- Админка ----------

class LoginIn(Input):
    email: Annotated[str, Field(min_length=3, max_length=200)]
    password: Annotated[str, Field(min_length=1, max_length=200)]


class PasswordIn(Input):
    current_password: Annotated[str, Field(min_length=1, max_length=200)]
    new_password: Annotated[str, Field(min_length=8, max_length=200)]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105 — тип токена по OAuth2, не секрет


class UserOut(ORM):
    id: int
    email: str
    name: str
    role: str
    sites: list[str] | None


Password = Annotated[str, Field(min_length=8, max_length=200)]
# None — доступ ко всем сайтам; пустой список запрещён: такой сотрудник не видел бы ничего
Sites = Annotated[list[str] | None, Field(min_length=1)]


class UserIn(Input):
    email: Annotated[str, Field(min_length=3, max_length=200)]
    name: Name
    password: Password
    role: Role = "staff"
    sites: Sites = None

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        if not EMAIL_RE.match(v):
            raise ValueError("Некорректный e-mail")
        return v


class UserPatch(Input):
    """Правка сотрудника владельцем. Поле sites передаётся явно: null — все сайты, список — только эти."""

    name: Name | None = None
    role: Role | None = None
    sites: Sites = None
    password: Password | None = None


class LeadPatch(Input):
    status: LeadStatus


class BookingPatch(Input):
    status: BookingStatus


class OrderPatch(Input):
    status: OrderStatus


class CatalogIn(Input):
    ref: Annotated[str, Field(min_length=1, max_length=60)]
    name: Annotated[str, Field(min_length=1, max_length=LIMITS["catalog_name"])]
    category: str = Field("", max_length=60)
    price: Annotated[int, Field(ge=1, le=10_000_000)]  # бесплатных позиций нет: 0 — почти всегда стёртое поле
    active: bool = True


class CatalogPatch(Input):
    name: str | None = Field(None, min_length=1, max_length=LIMITS["catalog_name"])
    price: int | None = Field(None, ge=1, le=10_000_000)
    active: bool | None = None


class Stats(BaseModel):
    leads: int
    bookings: int
    orders: int
    revenue: int
    new_leads: int
    by_day: list[dict]
    by_site: dict[str, int]
