"""Telegram-бот кофейни: меню, корзина, оформление заказа, уведомление админу."""

import asyncio
import logging
import os
import sqlite3
import sys
from collections.abc import Mapping

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()


def read_config(env: Mapping[str, str] = os.environ) -> tuple[str, int]:
    """Токен и Telegram ID администратора. Без них бот не запускается: иначе он принимал бы заказы,
    отвечал клиенту «Заказ принят», а администратор ничего бы не получил."""
    token = (env.get("BOT_TOKEN") or "").strip()
    try:
        admin_id = int((env.get("ADMIN_ID") or "").strip())
    except ValueError:
        admin_id = 0
    problems = []
    if not token:
        problems.append("BOT_TOKEN — токен бота от @BotFather")
    if admin_id <= 0:
        problems.append("ADMIN_ID — ваш числовой Telegram ID (узнать у @userinfobot)")
    if problems:
        sys.exit("Бот не запущен. Задайте в .env:\n- " + "\n- ".join(problems))
    return token, admin_id


try:
    ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
except ValueError:
    ADMIN_ID = 0  # main() всё равно остановит запуск с понятным сообщением

MENU = {
    "coffee": ("☕ Кофе", [("Капучино", 220), ("Латте", 240), ("Флэт уайт", 260)]),
    "bakery": ("🥐 Выпечка", [("Круассан", 180), ("Синнабон", 210)]),
    "dessert": ("🍰 Десерты", [("Чизкейк", 290), ("Тирамису", 320)]),
}

# ---------- База данных ----------
db = sqlite3.connect("cafe.db")
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
db.execute(
    "CREATE TABLE IF NOT EXISTS orders ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, items TEXT, total INTEGER, "
    "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
)
db.commit()

carts: dict[int, list[tuple[str, int]]] = {}

dp = Dispatcher()
log = logging.getLogger("cafe-bot")


# Данные кнопок: фабрики aiogram проверяют формат, а клиент Telegram может прислать что угодно
class Cat(CallbackData, prefix="cat"):
    key: str


class Add(CallbackData, prefix="add"):
    key: str
    idx: int


class Ready(CallbackData, prefix="ready"):
    order_id: int
    user_id: int


def menu_item(key: str, idx: int) -> tuple[str, int] | None:
    """Позиция меню или None, если такой нет (кнопка из старого меню или подделанные данные)."""
    items = MENU.get(key, ("", []))[1]
    return items[idx] if 0 <= idx < len(items) else None


async def show(call: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None = None) -> None:
    """Заменить текст сообщения. Повторное нажатие той же кнопки — не ошибка: Telegram отвечает «not modified»."""
    try:
        await call.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


# ---------- Клавиатуры ----------
def main_kb(user_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Меню", callback_data="menu")
    kb.button(text=f"🛒 Корзина ({len(carts.get(user_id, []))})", callback_data="cart")
    kb.button(text="📍 Адрес и часы", callback_data="info")
    kb.adjust(2, 1)
    return kb.as_markup()


def categories_kb():
    kb = InlineKeyboardBuilder()
    for key, (title, _) in MENU.items():
        kb.button(text=title, callback_data=Cat(key=key))
    kb.button(text="⬅️ Назад", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def category_kb(key: str, user_id: int):
    kb = InlineKeyboardBuilder()
    for i, (name, price) in enumerate(MENU[key][1]):
        kb.button(text=f"+ {name} — {price} ₽", callback_data=Add(key=key, idx=i))
    kb.button(text="⬅️ Категории", callback_data="menu")
    kb.button(text=f"🛒 Корзина ({len(carts.get(user_id, []))})", callback_data="cart")
    kb.adjust(1)
    return kb.as_markup()


def cart_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Оформить заказ", callback_data="checkout")
    kb.button(text="🗑 Очистить", callback_data="clear")
    kb.button(text="⬅️ В меню", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


# ---------- Хендлеры ----------
@dp.message(CommandStart())
async def start(message: Message):
    db.execute(
        "INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)",
        (message.from_user.id, message.from_user.full_name),
    )
    db.commit()
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        "Я бот кофейни «Зерно». Помогу сделать заказ без очереди.",
        reply_markup=main_kb(message.from_user.id),
    )


@dp.callback_query(F.data == "home")
async def home(call: CallbackQuery):
    await call.answer()
    await show(call, "Выберите, что хотите сделать 👇", main_kb(call.from_user.id))


@dp.callback_query(F.data == "menu")
async def menu(call: CallbackQuery):
    await call.answer()
    await show(call, "Выберите категорию:", categories_kb())


@dp.callback_query(Cat.filter())
async def category(call: CallbackQuery, callback_data: Cat):
    if callback_data.key not in MENU:
        await call.answer("Меню обновилось, откройте его заново", show_alert=True)
        return
    await call.answer()
    await show(call, MENU[callback_data.key][0], category_kb(callback_data.key, call.from_user.id))


@dp.callback_query(Add.filter())
async def add_to_cart(call: CallbackQuery, callback_data: Add):
    item = menu_item(callback_data.key, callback_data.idx)
    if not item:
        await call.answer("Меню обновилось, откройте его заново", show_alert=True)
        return
    carts.setdefault(call.from_user.id, []).append(item)
    await call.answer(f"✅ {item[0]} добавлен в корзину")
    try:
        await call.message.edit_reply_markup(reply_markup=category_kb(callback_data.key, call.from_user.id))
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@dp.callback_query(F.data == "cart")
async def show_cart(call: CallbackQuery):
    cart = carts.get(call.from_user.id, [])
    if not cart:
        await call.answer("Корзина пуста 🙂", show_alert=True)
        return
    await call.answer()
    lines = "\n".join(f"• {name} — {price} ₽" for name, price in cart)
    total = sum(price for _, price in cart)
    await show(call, f"🛒 Ваш заказ:\n\n{lines}\n\nИтого: {total} ₽", cart_kb())


@dp.callback_query(F.data == "clear")
async def clear_cart(call: CallbackQuery):
    carts.pop(call.from_user.id, None)
    await call.answer("Корзина очищена")
    await show(call, "Корзина очищена.", main_kb(call.from_user.id))


@dp.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery, bot: Bot):
    cart = carts.pop(call.from_user.id, [])
    if not cart:
        await call.answer("Корзина пуста", show_alert=True)
        return
    await call.answer()
    items = ", ".join(name for name, _ in cart)
    total = sum(price for _, price in cart)
    cur = db.execute(
        "INSERT INTO orders (user_id, items, total) VALUES (?, ?, ?)",
        (call.from_user.id, items, total),
    )
    db.commit()
    order_id = cur.lastrowid

    await show(
        call,
        f"🎉 Заказ №{order_id} принят!\nСумма: {total} ₽\n\n"
        "Будет готов через 10–15 минут. Мы пришлём уведомление.",
        main_kb(call.from_user.id),
    )

    if ADMIN_ID:
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Готов", callback_data=Ready(order_id=order_id, user_id=call.from_user.id))
        await bot.send_message(
            ADMIN_ID,
            f"🆕 Заказ №{order_id}\n"
            f"От: {call.from_user.full_name} (@{call.from_user.username or '—'})\n"
            f"Состав: {items}\nСумма: {total} ₽",
            reply_markup=kb.as_markup(),
        )


@dp.callback_query(Ready.filter())
async def order_ready(call: CallbackQuery, callback_data: Ready, bot: Bot):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Эта кнопка — для администратора", show_alert=True)
        return
    await bot.send_message(callback_data.user_id, f"☕ Заказ №{callback_data.order_id} готов! Заберите его на кассе.")
    await call.answer("Клиент уведомлён")
    await show(call, (call.message.text or "") + "\n\n✅ Клиент уведомлён")


@dp.callback_query(F.data == "info")
async def info(call: CallbackQuery):
    await call.answer()
    await show(call, "📍 ул. Примерная, 12\n🕗 Ежедневно 8:00–22:00\n📞 +7 (900) 000-00-00", main_kb(call.from_user.id))


@dp.callback_query()
async def unknown_button(call: CallbackQuery):
    """Кнопка, которую бот не знает: из старого сообщения или с подделанными данными. Отвечаем, а не молчим."""
    log.info("Неизвестная кнопка: %r", call.data)
    await call.answer("Меню обновилось, откройте его заново: /start", show_alert=True)


@dp.message(Command("broadcast"))
async def broadcast(message: Message, bot: Bot):
    """Рассылка всем пользователям: /broadcast текст (только для админа)."""
    if message.from_user.id != ADMIN_ID:
        return
    text = message.text.removeprefix("/broadcast").strip()
    if not text:
        await message.answer("Использование: /broadcast текст сообщения")
        return
    sent = 0
    for (user_id,) in db.execute("SELECT id FROM users"):
        try:
            await bot.send_message(user_id, text)
            sent += 1
        except Exception:  # noqa: BLE001, S110 — разбор ошибок рассылки — BOT-004
            pass
        await asyncio.sleep(0.05)
    await message.answer(f"Рассылка завершена: {sent} получателей.")


async def main():
    logging.basicConfig(level=logging.INFO)
    token, _ = read_config()
    bot = Bot(token)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
