"""Админка: расписание по неделям (BUG-008) и пагинация заказов."""

from conftest import demo_login
from playwright.sync_api import expect


def open_admin(page, site, view):
    page.goto(f"{site}/admin/")
    demo_login(page, site)
    page.goto(f"{site}/admin/#{view}")
    page.reload()


def test_bookings_week_navigation(page, site, errors):
    page.goto(f"{site}/projects/fitness/")
    # Запись через три недели: в «последних 100» она бы была, но в расписании этой недели её быть не должно
    day = page.evaluate("() => PortfolioAPI.siteToday('fitness', 13)")
    page.evaluate("""(day) => PortfolioAPI.createBooking('fitness', { resource: 'Кроссфит', starts_at: `${day}T18:00:00`, name: 'Через две недели', phone: '+79001234567' })""", day)
    open_admin(page, site, "bookings")
    toolbar = page.locator("#content .toolbar")
    expect(toolbar).to_contain_text("Эта неделя")
    expect(page.locator("#content")).not_to_contain_text("Через две недели")
    for _ in range(2):
        toolbar.locator("[data-week='1']").click()
        toolbar = page.locator("#content .toolbar")
        if page.locator("#content", has_text="Через две недели").count():
            break
    expect(page.locator("#content")).to_contain_text("Через две недели")


def test_orders_have_pager(page, site, errors):
    open_admin(page, site, "orders")
    expect(page.locator("#content .pager")).to_contain_text("из ")


def test_polling_does_not_steal_focus(page, site, api, errors):
    # BUG-012: опрос API раз в 15 секунд перерисовывал раздел и закрывал открытый список статусов
    import json
    import urllib.request

    from conftest import OWNER
    body = {"kind": "table", "name": "Опрос", "phone": "+79001234567"}
    post = lambda: urllib.request.urlopen(urllib.request.Request(  # noqa: E731
        f"{api}/api/v1/sites/cafe/leads", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}))
    post()
    page.clock.install()
    page.goto(f"{site}/admin/?api={api}")
    page.locator("#loginForm [name=email]").fill(OWNER[0])
    page.locator("#loginForm [name=password]").fill(OWNER[1])
    page.locator("#loginForm button[type=submit]").click()
    page.locator("[data-view=leads]").click()
    expect(page.locator("#q")).to_be_visible()  # раздел «Заявки» уже отрисован, а не «Обзор»
    select = page.locator("[data-lead]").first
    select.focus()
    marker = select.evaluate("(el) => (el.dataset.mark = 'same')")
    page.clock.run_for(16_000)  # данные не менялись: раздел не перерисован
    page.wait_for_timeout(1500)  # ответ API на опрос приходит в реальном времени
    assert select.evaluate("(el) => el.dataset.mark") == marker == "same"
    post()
    page.clock.run_for(16_000)  # данные изменились, но фокус в разделе — ждём
    page.wait_for_timeout(1500)
    assert page.locator("[data-lead]").first.evaluate("(el) => el.dataset.mark") == "same"
    page.locator("#viewTitle").click()  # фокус ушёл — обновление применяется
    page.locator("body").focus()
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    page.clock.run_for(16_000)
    expect(page.locator("#content")).to_contain_text("из 2")
