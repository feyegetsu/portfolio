"""Схемы запросов и ответов. Всё, что приходит с публичных форм, валидируется здесь."""

import re
from datetime import datetime
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

PHONE_RE = re.compile(r"^\+?\d{10,15}$")
T = TypeVar("T")

Name = Annotated[str, Field(min_length=1, max_length=100)]
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


class Honeypot(BaseModel):
    # Скрытое поле: люди его не видят и не заполняют, а спам-боты заполняют
    website: str = ""


# ---------- Публичные формы ----------

class LeadIn(Honeypot):
    kind: Annotated[str, Field(min_length=1, max_length=40)]
    name: str = Field("", max_length=100)
    phone: str = ""
    email: str = Field("", max_length=200)
    message: str = Field("", max_length=2000)
    data: dict = Field(default_factory=dict)

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_phone(v) if v else v


class BookingIn(Honeypot):
    resource: Annotated[str, Field(min_length=1, max_length=100)]
    service: str = Field("", max_length=100)
    starts_at: datetime
    name: Name
    phone: str

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        return normalize_phone(v)


class OrderItem(BaseModel):
    ref: str = Field("", max_length=60)
    name: Annotated[str, Field(min_length=1, max_length=200)]
    qty: Annotated[int, Field(ge=1, le=99)]
    price: Annotated[int, Field(ge=0, le=1_000_000)]


class OrderIn(Honeypot):
    items: Annotated[list[OrderItem], Field(min_length=1, max_length=50)]
    name: Name
    phone: str
    address: str = Field("", max_length=300)
    mode: Literal["delivery", "pickup"] = "delivery"
    comment: str = Field("", max_length=1000)

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


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int


# ---------- Админка ----------

class LoginIn(BaseModel):
    email: Annotated[str, Field(min_length=3, max_length=200)]
    password: Annotated[str, Field(min_length=1, max_length=200)]


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(ORM):
    id: int
    email: str
    name: str
    role: str
    sites: list[str] | None


class UserIn(BaseModel):
    email: Annotated[str, Field(min_length=3, max_length=200)]
    name: Name
    password: Annotated[str, Field(min_length=8, max_length=200)]
    role: Role = "staff"
    sites: list[str] | None = None


class LeadPatch(BaseModel):
    status: LeadStatus


class BookingPatch(BaseModel):
    status: BookingStatus


class OrderPatch(BaseModel):
    status: OrderStatus


class CatalogIn(BaseModel):
    ref: Annotated[str, Field(min_length=1, max_length=60)]
    name: Annotated[str, Field(min_length=1, max_length=200)]
    category: str = Field("", max_length=60)
    price: Annotated[int, Field(ge=0, le=10_000_000)]
    active: bool = True


class CatalogPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=200)
    price: int | None = Field(None, ge=0, le=10_000_000)
    active: bool | None = None


class Stats(BaseModel):
    leads: int
    bookings: int
    orders: int
    revenue: int
    new_leads: int
    by_day: list[dict]
    by_site: dict[str, int]
