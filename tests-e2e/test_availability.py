"""BUG-005: формы записи показывают настоящую занятость — после 10 броней ресторана на 20:00 это время неактивно."""

import json
import urllib.request

from playwright.sync_api import expect

BOOK_TEN = """async (day) => {
  for (let i = 0; i < 10; i++) {
    await PortfolioAPI.createBooking('restaurant', { resource: 'Стол на 2', starts_at: `${day}T20:00:00`, name: `Гость ${i}`, phone: '+79001234567' });
  }
}"""
# Ближайший вторник (ресторан открыт) не раньше завтрашнего дня, по времени ресторана
NEXT_TUESDAY = """() => { for (let i = 1; i < 8; i++) { const d = PortfolioAPI.siteToday('restaurant', i);
  if (new Date(`${d}T12:00:00`).getDay() === 2) return [d, i]; } }"""


def check_restaurant(page, index):
    page.locator(f"#dates [data-d='{index}']").click()
    expect(page.locator("#times [data-t='20:00']")).to_be_disabled()
    expect(page.locator("#times [data-t='19:30']")).to_be_enabled()


def test_full_slot_disabled_in_demo(page, site, errors):
    page.goto(f"{site}/projects/restaurant/")
    day, index = page.evaluate(NEXT_TUESDAY)
    page.evaluate(BOOK_TEN, day)
    page.reload()
    check_restaurant(page, index)


def test_full_slot_disabled_with_real_api(page, site, api, errors):
    page.goto(f"{site}/projects/restaurant/?api={api}")
    day, index = page.evaluate(NEXT_TUESDAY)
    for i in range(10):
        body = {"resource": "Стол на 4", "starts_at": f"{day}T20:00:00", "name": f"API {i}", "phone": "+79001234567"}
        urllib.request.urlopen(urllib.request.Request(f"{api}/api/v1/sites/restaurant/bookings", data=json.dumps(body).encode(),
                                                      headers={"Content-Type": "application/json"}))
    page.reload()
    check_restaurant(page, index)


def test_fitness_shows_seats_from_api(page, site, errors):
    page.goto(f"{site}/projects/fitness/")
    first = page.locator("#classes .cls").first
    expect(first.locator(".spots")).to_contain_text("Свободно")
    name = first.locator("h3").inner_text()
    cap = page.evaluate("(n) => PortfolioAPI.rules('fitness').resources[n]", name)
    expect(first.locator(".spots")).to_contain_text(f"из {cap}")
