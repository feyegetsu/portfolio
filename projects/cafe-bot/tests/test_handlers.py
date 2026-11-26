"""BOT-005: оформление заказа, кнопка «Готов» и рассылка."""

from conftest import ADMIN, callback, message

import bot as cafe


async def test_checkout_saves_order_and_notifies_admin(bot):
    await cafe.add_to_cart(callback("add:coffee:0"))
    await cafe.add_to_cart(callback("add:bakery:1"))
    call = callback("checkout")
    await cafe.checkout(call, bot)
    text = call.message.edit_text.await_args.args[0]
    assert "принят" in text and "430" in text  # 220 + 210
    chat_id, admin_text = bot.send_message.await_args.args
    assert chat_id == ADMIN and "Капучино" in admin_text


async def test_order_ready_only_for_admin(bot):
    stranger = callback("ready:5:7", uid=1, text="Заказ")
    await cafe.order_ready(stranger, bot)
    bot.send_message.assert_not_awaited()
    admin = callback("ready:5:7", uid=ADMIN, text="Заказ")
    await cafe.order_ready(admin, bot)
    assert bot.send_message.await_args.args[0] == 7


async def test_broadcast_reaches_users(bot):
    await cafe.start(message("/start", uid=7))
    await cafe.start(message("/start", uid=8))
    report = message("/broadcast Скидка 10%", uid=ADMIN)
    await cafe.broadcast(report, bot)
    assert {c.args[0] for c in bot.send_message.await_args_list} >= {7, 8}
    assert "получател" in report.answer.await_args.args[0]
