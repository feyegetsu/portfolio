"""BOT-005: оформление заказа, кнопка «Готов» и рассылка."""

from conftest import ADMIN, callback, message

import bot as cafe


async def test_checkout_saves_order_and_notifies_admin(bot, store):
    await cafe.add_to_cart(callback("add:coffee:0"), cafe.Add(key="coffee", idx=0), store)
    await cafe.add_to_cart(callback("add:bakery:1"), cafe.Add(key="bakery", idx=1), store)
    call = callback("checkout")
    await cafe.checkout(call, bot, store, ADMIN)
    text = call.message.edit_text.await_args.args[0]
    assert "принят" in text and "430" in text  # 220 + 210
    chat_id, admin_text = bot.send_message.await_args.args
    assert chat_id == ADMIN and "Капучино" in admin_text
    assert await store.cart(7) == []  # корзина оформлена


async def test_empty_cart_checkout(bot, store):
    call = callback("checkout")
    await cafe.checkout(call, bot, store, ADMIN)
    assert call.answer.await_args.kwargs.get("show_alert") is True
    bot.send_message.assert_not_awaited()


async def test_order_ready_only_for_admin(bot):
    stranger = callback("ready:5:7", uid=1, text="Заказ")
    await cafe.order_ready(stranger, cafe.Ready(order_id=5, user_id=7), bot, ADMIN)
    bot.send_message.assert_not_awaited()
    admin = callback("ready:5:7", uid=ADMIN, text="Заказ")
    await cafe.order_ready(admin, cafe.Ready(order_id=5, user_id=7), bot, ADMIN)
    assert bot.send_message.await_args.args[0] == 7


async def test_broadcast_reaches_users(bot, store):
    await cafe.start(message("/start", uid=7), store)
    await cafe.start(message("/start", uid=8), store)
    report = message("/broadcast Скидка 10%", uid=ADMIN)
    await cafe.broadcast(report, bot, store, ADMIN)
    assert {c.args[0] for c in bot.send_message.await_args_list} >= {7, 8}
    assert "Отправлено: 2" in report.answer.await_args.args[0] or "2 получател" in report.answer.await_args.args[0]


async def test_broadcast_only_for_admin(bot, store):
    await cafe.broadcast(message("/broadcast спам", uid=7), bot, store, ADMIN)
    bot.send_message.assert_not_awaited()
