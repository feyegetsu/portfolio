"""Начальные данные: первый владелец и каталоги Mini App и суши. Запускается при старте и ничего не дублирует."""

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


# ref совпадает с id позиции в projects/sushi
SUSHI_MENU = [
    ("s1", "Сет «Кайсэн»", "Сеты", 2490),
    ("s2", "Сет «Филадельфия»", "Сеты", 1890),
    ("s3", "Сет для двоих", "Сеты", 1390),
    ("s4", "Филадельфия", "Роллы", 590),
    ("s5", "Калифорния", "Роллы", 490),
    ("s6", "Радуга", "Роллы", 650),
    ("s7", "Маки с огурцом", "Роллы", 190),
    ("s8", "Красный дракон", "Роллы", 690),
    ("s9", "Запечённый с лососем", "Запечённые", 560),
    ("s10", "Запечённый с крабом", "Запечённые", 520),
    ("s11", "Нигири с лососем", "Нигири и сашими", 220),
    ("s12", "Сашими-ассорти", "Нигири и сашими", 990),
    ("s13", "Нигири микс", "Нигири и сашими", 690),
    ("s14", "Рамен тонкоцу", "Горячее", 590),
    ("s15", "Острый рамен с курицей", "Горячее", 560),
    ("s16", "Гёдза со свининой", "Горячее", 390),
    ("s17", "Якитори", "Горячее", 450),
]

CATALOGS = {"miniapp": MINIAPP_MENU, "sushi": SUSHI_MENU}


def seed(db: Session) -> None:
    if not db.scalar(select(func.count()).select_from(User)):
        db.add(User(email=settings.owner_email.lower(), name="Владелец", role="owner", sites=None,
                    password_hash=hash_password(settings.owner_password)))
    for site, menu in CATALOGS.items():
        if not db.scalar(select(func.count()).select_from(CatalogItem).where(CatalogItem.site == site)):
            db.add_all(CatalogItem(site=site, ref=ref, name=name, category=cat, price=price) for ref, name, cat, price in menu)
    db.commit()
