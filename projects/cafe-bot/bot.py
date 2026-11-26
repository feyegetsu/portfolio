"""Telegram-бот кофейни: меню, корзина, оформление заказа, уведомление админу."""

import asyncio
import logging
import os
import sqlite3
import sys
import threading
from collections.abc import Mapping
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandStart
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")


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


def db_path(env: Mapping[str, str] = os.environ) -> Path:
    """Файл базы — из DB_PATH, по умолчанию рядом с bot.py, а не в той папке, откуда бот запустили."""
    return Path(env.get("DB_PATH") or HERE / "cafe.db")


MENU = {
    "coffee": ("☕ Кофе", [("Капучино", 220), ("Латте", 240), ("Флэт уайт", 260)]),
    "bakery": ("🥐 Выпечка", [("Круассан", 180), ("Синнабон", 210)]),
    "dessert": ("🍰 Десерты", [("Чизкейк", 290), ("Тирамису", 320)]),
}


# ---------- База данных ----------
class Storage:
    """Пользователи, заказы и корзины в SQLite. Корзины тоже в базе: перезапуск бота их не стирает.

    Методы с приставкой a — асинхронные: запрос идёт в потоке (asyncio.to_thread), цикл событий не ждёт диск.
    """

    def __init__(self, path: Path | str) -> None:
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()  # одно соединение на несколько потоков: запросы по очереди
        with self.lock, self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, active INTEGER NOT NULL DEFAULT 1)")
            # База прежней версии: колонки active ещё нет
            if "active" not in [c[1] for c in self.db.execute("PRAGMA table_info(users)")]:
                self.db.execute("ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS orders ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, items TEXT, total INTEGER, "
                "created_at TEXT DEFAULT CURRENT_TIMESTAMP)"
            )
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS carts (pos INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, name TEXT, price INTEGER)"
            )

    def _run(self, sql: str, args: tuple = ()) -> list[tuple]:
        with self.lock, self.db:
            cur = self.db.execute(sql, args)
            return cur.fetchall() if cur.description else [(cur.lastrowid,)]

    async def _a(self, sql: str, args: tuple = ()) -> list[tuple]:
        return await asyncio.to_thread(self._run, sql, args)

    async def add_user(self, user_id: int, name: str) -> None:
        # /start снова делает пользователя активным: он разблокировал бота
        await self._a("INSERT INTO users (id, name, active) VALUES (?, ?, 1) ON CONFLICT(id) DO UPDATE SET active = 1", (user_id, name))

    async def user_ids(self) -> list[int]:
        """Получатели рассылки: пользователи, которые не заблокировали бота."""
        return [row[0] for row in await self._a("SELECT id FROM users WHERE active = 1")]

    async def deactivate(self, user_id: int) -> None:
        await self._a("UPDATE users SET active = 0 WHERE id = ?", (user_id,))

    async def cart(self, user_id: int) -> list[tuple[str, int]]:
        return [(n, p) for n, p in await self._a("SELECT name, price FROM carts WHERE user_id = ? ORDER BY pos", (user_id,))]

    async def add_to_cart(self, user_id: int, item: tuple[str, int]) -> None:
        await self._a("INSERT INTO carts (user_id, name, price) VALUES (?, ?, ?)", (user_id, *item))

    async def clear_cart(self, user_id: int) -> None:
        await self._a("DELETE FROM carts WHERE user_id = ?", (user_id,))

    async def create_order(self, user_id: int, items: str, total: int) -> int:
        return (await self._a("INSERT INTO orders (user_id, items, total) VALUES (?, ?, ?)", (user_id, items, total)))[0][0]

    def close(self) -> None:
        self.db.close()


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
def main_kb(cart_size: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Меню", callback_data="menu")
    kb.button(text=f"🛒 Корзина ({cart_size})", callback_data="cart")
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


def category_kb(key: str, cart_size: int):
    kb = InlineKeyboardBuilder()
    for i, (name, price) in enumerate(MENU[key][1]):
        kb.button(text=f"+ {name} — {price} ₽", callback_data=Add(key=key, idx=i))
    kb.button(text="⬅️ Категории", callback_data="menu")
    kb.button(text=f"🛒 Корзина ({cart_size})", callback_data="cart")
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
# store и admin_id передаются в каждый обработчик из dp.start_polling(..., store=..., admin_id=...)
@dp.message(CommandStart())
async def start(message: Message, store: Storage):
    await store.add_user(message.from_user.id, message.from_user.full_name)
    await message.answer(
        f"Привет, {message.from_user.first_name}! 👋\n"
        "Я бот кофейни «Зерно». Помогу сделать заказ без очереди.",
        reply_markup=main_kb(len(await store.cart(message.from_user.id))),
    )


@dp.callback_query(F.data == "home")
async def home(call: CallbackQuery, store: Storage):
    await call.answer()
    await show(call, "Выберите, что хотите сделать 👇", main_kb(len(await store.cart(call.from_user.id))))


@dp.callback_query(F.data == "menu")
async def menu(call: CallbackQuery):
    await call.answer()
    await show(call, "Выберите категорию:", categories_kb())


@dp.callback_query(Cat.filter())
async def category(call: CallbackQuery, callback_data: Cat, store: Storage):
    if callback_data.key not in MENU:
        await call.answer("Меню обновилось, откройте его заново", show_alert=True)
        return
    await call.answer()
    await show(call, MENU[callback_data.key][0], category_kb(callback_data.key, len(await store.cart(call.from_user.id))))


@dp.callback_query(Add.filter())
async def add_to_cart(call: CallbackQuery, callback_data: Add, store: Storage):
    item = menu_item(callback_data.key, callback_data.idx)
    if not item:
        await call.answer("Меню обновилось, откройте его заново", show_alert=True)
        return
    await store.add_to_cart(call.from_user.id, item)
    await call.answer(f"✅ {item[0]} добавлен в корзину")
    try:
        await call.message.edit_reply_markup(reply_markup=category_kb(callback_data.key, len(await store.cart(call.from_user.id))))
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


@dp.callback_query(F.data == "cart")
async def show_cart(call: CallbackQuery, store: Storage):
    cart = await store.cart(call.from_user.id)
    if not cart:
        await call.answer("Корзина пуста 🙂", show_alert=True)
        return
    await call.answer()
    lines = "\n".join(f"• {name} — {price} ₽" for name, price in cart)
    total = sum(price for _, price in cart)
    await show(call, f"🛒 Ваш заказ:\n\n{lines}\n\nИтого: {total} ₽", cart_kb())


@dp.callback_query(F.data == "clear")
async def clear_cart(call: CallbackQuery, store: Storage):
    await store.clear_cart(call.from_user.id)
    await call.answer("Корзина очищена")
    await show(call, "Корзина очищена.", main_kb(0))


@dp.callback_query(F.data == "checkout")
async def checkout(call: CallbackQuery, bot: Bot, store: Storage, admin_id: int):
    cart = await store.cart(call.from_user.id)
    if not cart:
        await call.answer("Корзина пуста", show_alert=True)
        return
    await call.answer()
    items = ", ".join(name for name, _ in cart)
    total = sum(price for _, price in cart)
    order_id = await store.create_order(call.from_user.id, items, total)
    await store.clear_cart(call.from_user.id)

    await show(
        call,
        f"🎉 Заказ №{order_id} принят!\nСумма: {total} ₽\n\n"
        "Будет готов через 10–15 минут. Мы пришлём уведомление.",
        main_kb(0),
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Готов", callback_data=Ready(order_id=order_id, user_id=call.from_user.id))
    await bot.send_message(
        admin_id,
        f"🆕 Заказ №{order_id}\n"
        f"От: {call.from_user.full_name} (@{call.from_user.username or '—'})\n"
        f"Состав: {items}\nСумма: {total} ₽",
        reply_markup=kb.as_markup(),
    )


@dp.callback_query(Ready.filter())
async def order_ready(call: CallbackQuery, callback_data: Ready, bot: Bot, admin_id: int):
    if call.from_user.id != admin_id:
        await call.answer("Эта кнопка — для администратора", show_alert=True)
        return
    await bot.send_message(callback_data.user_id, f"☕ Заказ №{callback_data.order_id} готов! Заберите его на кассе.")
    await call.answer("Клиент уведомлён")
    await show(call, (call.message.text or "") + "\n\n✅ Клиент уведомлён")


@dp.callback_query(F.data == "info")
async def info(call: CallbackQuery, store: Storage):
    await call.answer()
    await show(call, "📍 ул. Примерная, 12\n🕗 Ежедневно 8:00–22:00\n📞 +7 (900) 000-00-00",
               main_kb(len(await store.cart(call.from_user.id))))


@dp.callback_query()
async def unknown_button(call: CallbackQuery):
    """Кнопка, которую бот не знает: из старого сообщения или с подделанными данными. Отвечаем, а не молчим."""
    log.info("Неизвестная кнопка: %r", call.data)
    await call.answer("Меню обновилось, откройте его заново: /start", show_alert=True)


async def send_all(bot: Bot, store: Storage, text: str, pause: float = 0.05, retries: int = 3) -> dict[str, int]:
    """Рассылка с учётом ограничений Telegram. Флуд-лимит — ждём, сколько просит Telegram, и повторяем;
    бот заблокирован — пользователь больше не получает рассылок; прочие ошибки — в лог и в отчёт."""
    report = {"sent": 0, "blocked": 0, "failed": 0}
    for user_id in await store.user_ids():
        for attempt in range(retries):
            try:
                await bot.send_message(user_id, text)
                report["sent"] += 1
                break
            except TelegramRetryAfter as e:
                if attempt == retries - 1:
                    log.warning("Рассылка: флуд-лимит для %s не прошёл за %s попытки", user_id, retries)
                    report["failed"] += 1
                    break
                await asyncio.sleep(e.retry_after)
            except TelegramForbiddenError:
                await store.deactivate(user_id)
                report["blocked"] += 1
                break
            except TelegramAPIError as e:
                log.warning("Рассылка: не доставлено %s: %s", user_id, e)
                report["failed"] += 1
                break
        await asyncio.sleep(pause)
    return report


@dp.message(Command("broadcast"))
async def broadcast(message: Message, bot: Bot, store: Storage, admin_id: int):
    """Рассылка всем пользователям: /broadcast текст (только для админа)."""
    if message.from_user.id != admin_id:
        return
    text = message.text.removeprefix("/broadcast").strip()
    if not text:
        await message.answer("Использование: /broadcast текст сообщения")
        return
    r = await send_all(bot, store, text)
    await message.answer(f"Рассылка завершена.\nОтправлено: {r['sent']}\nЗаблокировали бота: {r['blocked']}\nОшибки: {r['failed']}")


async def main():
    logging.basicConfig(level=logging.INFO)
    token, admin_id = read_config()
    store = Storage(db_path())
    bot = Bot(token)
    try:
        await dp.start_polling(bot, store=store, admin_id=admin_id)
    finally:
        store.close()


if __name__ == "__main__":
    asyncio.run(main())
