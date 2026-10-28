"""Начальные данные: первый владелец и каталог Mini App. Запускается при старте и ничего не дублирует."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import settings
from .models import CatalogItem, User
from .security import hash_password

# ref совпадает с id блюда в projects/miniapp
MINIAPP_MENU = [
    ("1", "Маргарита", "Пицца", 549), ("2", "Пепперони", "Пицца", 649), ("3", "Овощная", "Пицца", 599),
    ("4", "Четыре сезона", "Пицца", 699), ("5", "Классик", "Бургеры", 429), ("6", "Пулд-порк", "Бургеры", 469),
    ("7", "Бургер + фри", "Бургеры", 549), ("8", "Филадельфия", "Роллы", 589), ("9", "Сет «Лис»", "Роллы", 1590),
    ("10", "Нигири микс", "Роллы", 690), ("11", "Боул с курицей", "Боулы", 459), ("12", "Поке с лососем", "Боулы", 549),
    ("13", "Паста с морепродуктами", "Горячее", 589), ("14", "Пенне арабьята", "Горячее", 399),
    ("15", "Стейк с фри", "Горячее", 890), ("16", "Лимонады", "Напитки", 219),
]


def seed(db: Session) -> None:
    if not db.scalar(select(func.count()).select_from(User)):
        db.add(User(email=settings.owner_email.lower(), name="Владелец", role="owner", sites=None,
                    password_hash=hash_password(settings.owner_password)))
    if not db.scalar(select(func.count()).select_from(CatalogItem).where(CatalogItem.site == "miniapp")):
        db.add_all(CatalogItem(site="miniapp", ref=ref, name=name, category=cat, price=price) for ref, name, cat, price in MINIAPP_MENU)
    db.commit()
