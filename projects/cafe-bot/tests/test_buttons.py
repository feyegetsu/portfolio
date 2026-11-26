"""BOT-002: каждая кнопка получает ответ, подделанные данные и повторные нажатия не роняют бота."""

from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText
from conftest import callback

import bot as cafe


@pytest.mark.parametrize("handler, data, args", [
    (cafe.home, "home", ()),
    (cafe.menu, "menu", ()),
    (cafe.info, "info", ()),
    (cafe.clear_cart, "clear", ()),
    (cafe.category, "cat:coffee", (cafe.Cat(key="coffee"),)),
    (cafe.unknown_button, "что-то старое", ()),
])
async def test_every_button_is_answered(handler, data, args):
    call = callback(data)
    await handler(call, *args)
    call.answer.assert_awaited()


async def test_forged_item_does_not_crash():
    call = callback("add:coffee:9")
    await cafe.add_to_cart(call, cafe.Add(key="coffee", idx=9))
    assert call.answer.await_args.kwargs.get("show_alert") is True
    call = callback("add:nope:0")
    await cafe.add_to_cart(call, cafe.Add(key="nope", idx=0))
    call.answer.assert_awaited()
    call = callback("cat:nope")
    await cafe.category(call, cafe.Cat(key="nope"))
    assert call.answer.await_args.kwargs.get("show_alert") is True


async def test_same_screen_twice_is_not_an_error():
    call = callback("menu")
    call.message.edit_text = AsyncMock(side_effect=TelegramBadRequest(EditMessageText(text="x"), "Bad Request: message is not modified"))
    await cafe.menu(call)  # не падает
    call.answer.assert_awaited()


def test_callback_data_is_validated():
    with pytest.raises(ValueError):
        cafe.Add.unpack("add:coffee:два")
    assert cafe.Ready.unpack("ready:5:7") == cafe.Ready(order_id=5, user_id=7)
