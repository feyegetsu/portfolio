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
