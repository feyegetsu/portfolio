"""Telegram-бот кофейни: меню, корзина, оформление заказа, уведомление админу."""

import asyncio
import logging
import os
import sqlite3

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

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
        kb.button(text=title, callback_data=f"cat:{key}")
    kb.button(text="⬅️ Назад", callback_data="home")
    kb.adjust(1)
    return kb.as_markup()


def category_kb(key: str, user_id: int):
    kb = InlineKeyboardBuilder()
    for i, (name, price) in enumerate(MENU[key][1]):
        kb.button(text=f"+ {name} — {price} ₽", callback_data=f"add:{key}:{i}")
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
    await call.message.edit_text("Выберите, что хотите сделать 👇", reply_markup=main_kb(call.from_user.id))


@dp.callback_query(F.data == "menu")
async def menu(call: CallbackQuery):
    await call.message.edit_text("Выберите категорию:", reply_markup=categories_kb())


@dp.callback_query(F.data.startswith("cat:"))
async def category(call: CallbackQuery):
    key = call.data.split(":")[1]
    await call.message.edit_text(MENU[key][0], reply_markup=category_kb(key, call.from_user.id))


@dp.callback_query(F.data.startswith("add:"))
async def add_to_cart(call: CallbackQuery):
    _, key, idx = call.data.split(":")
    item = MENU[key][1][int(idx)]
    carts.setdefault(call.from_user.id, []).append(item)
    await call.answer(f"✅ {item[0]} добавлен в корзину")
    await call.message.edit_reply_markup(reply_markup=category_kb(key, call.from_user.id))


@dp.callback_query(F.data == "cart")
async def show_cart(call: CallbackQuery):
    cart = carts.get(call.from_user.id, [])
    if not cart:
        await call.answer("Корзина пуста 🙂", show_alert=True)
        return
    lines = "\n".join(f"• {name} — {price} ₽" for name, price in cart)
    total = sum(price for _, price in cart)
    await call.message.edit_text(f"🛒 Ваш заказ:\n\n{lines}\n\nИтого: {total} ₽", reply_markup=cart_kb())


@dp.callback_query(F.data == "clear")
async def clear_cart(call: CallbackQuery):
    carts.pop(call.from_user.id, None)
    await call.message.edit_text("Корзина очищена.", reply_markup=main_kb(call.from_user.id))


@dp.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery, bot: Bot):
    cart = carts.pop(call.from_user.id, [])
    if not cart:
        await call.answer("Корзина пуста", show_alert=True)
        return
    items = ", ".join(name for name, _ in cart)
    total = sum(price for _, price in cart)
    cur = db.execute(
        "INSERT INTO orders (user_id, items, total) VALUES (?, ?, ?)",
        (call.from_user.id, items, total),
    )
    db.commit()
    order_id = cur.lastrowid

    await call.message.edit_text(
        f"🎉 Заказ №{order_id} принят!\nСумма: {total} ₽\n\n"
        "Будет готов через 10–15 минут. Мы пришлём уведомление.",
        reply_markup=main_kb(call.from_user.id),
    )

    if ADMIN_ID:
        kb = InlineKeyboardBuilder()
        kb.button(text="✅ Готов", callback_data=f"ready:{order_id}:{call.from_user.id}")
        await bot.send_message(
            ADMIN_ID,
            f"🆕 Заказ №{order_id}\n"
            f"От: {call.from_user.full_name} (@{call.from_user.username or '—'})\n"
            f"Состав: {items}\nСумма: {total} ₽",
            reply_markup=kb.as_markup(),
        )


@dp.callback_query(F.data.startswith("ready:"))
async def order_ready(call: CallbackQuery, bot: Bot):
    if call.from_user.id != ADMIN_ID:
        return
    _, order_id, user_id = call.data.split(":")
    await bot.send_message(int(user_id), f"☕ Заказ №{order_id} готов! Заберите его на кассе.")
    await call.message.edit_text(call.message.text + "\n\n✅ Клиент уведомлён")


@dp.callback_query(F.data == "info")
async def info(call: CallbackQuery):
    await call.message.edit_text(
        "📍 ул. Примерная, 12\n🕗 Ежедневно 8:00–22:00\n📞 +7 (900) 000-00-00",
        reply_markup=main_kb(call.from_user.id),
    )


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
        except Exception:
            pass
        await asyncio.sleep(0.05)
    await message.answer(f"Рассылка завершена: {sent} получателей.")


async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(BOT_TOKEN)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
