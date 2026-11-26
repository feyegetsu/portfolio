"""BOT-004: рассылка ждёт флуд-лимит, отключает заблокировавших и считает ошибки."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.methods import SendMessage
from conftest import ADMIN, message

import bot as cafe

METHOD = SendMessage(chat_id=1, text="x")


async def users(store, *ids):
    for uid in ids:
        await store.add_user(uid, f"u{uid}")


async def test_retry_after_is_respected(store):
    await users(store, 1)
    send = AsyncMock(side_effect=[TelegramRetryAfter(METHOD, "Flood", retry_after=0), None])
    report = await cafe.send_all(SimpleNamespace(send_message=send), store, "hi", pause=0)
    assert send.await_count == 2  # повторили после ожидания
    assert report == {"sent": 1, "blocked": 0, "failed": 0}


async def test_blocked_users_are_deactivated(store):
    await users(store, 1, 2)
    send = AsyncMock(side_effect=[TelegramForbiddenError(METHOD, "Forbidden: bot was blocked by the user"), None])
    report = await cafe.send_all(SimpleNamespace(send_message=send), store, "hi", pause=0)
    assert report == {"sent": 1, "blocked": 1, "failed": 0}
    assert await store.user_ids() == [2]
    await store.add_user(1, "u1")  # снова нажал /start
    assert sorted(await store.user_ids()) == [1, 2]


async def test_other_errors_are_counted_and_logged(store, caplog):
    await users(store, 1)
    send = AsyncMock(side_effect=TelegramBadRequest(METHOD, "Bad Request: chat not found"))
    report = await cafe.send_all(SimpleNamespace(send_message=send), store, "hi", pause=0)
    assert report == {"sent": 0, "blocked": 0, "failed": 1}
    assert "chat not found" in caplog.text


async def test_report_to_admin(store):
    await users(store, 1)
    bot = SimpleNamespace(send_message=AsyncMock())
    answer = message("/broadcast Акция", uid=ADMIN)
    await cafe.broadcast(answer, bot, store, ADMIN)
    assert "Отправлено: 1" in answer.answer.await_args.args[0]
