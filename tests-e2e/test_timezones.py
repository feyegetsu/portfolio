"""BUG-006: «сегодня» на демо — по московскому времени заведения, а не по часам посетителя и не по UTC."""

from datetime import UTC, datetime

import pytest

CASES = [
    # (пояс посетителя, момент в UTC, какой день в Москве)
    ("Asia/Novosibirsk", datetime(2026, 11, 19, 18, 30, tzinfo=UTC), "2026-11-19"),  # у посетителя уже 20-е, 01:30
    ("America/New_York", datetime(2026, 11, 20, 2, 30, tzinfo=UTC), "2026-11-20"),   # у посетителя ещё 19-е, 21:30
    ("Europe/Moscow", datetime(2026, 11, 19, 22, 30, tzinfo=UTC), "2026-11-20"),     # в Москве 01:30: по UTC ещё вчера
]


@pytest.mark.parametrize("tz, moment, msk_day", CASES, ids=[c[0] for c in CASES])
def test_today_follows_venue_time(browser, site, tz, moment, msk_day):
    ctx = browser.new_context(timezone_id=tz, locale="ru-RU")
    page = ctx.new_page()
    page.clock.install(time=moment)

    page.goto(f"{site}/projects/barbershop/")
    first_day = page.locator("#days .day").first.locator("b").inner_text()
    assert first_day == str(int(msk_day[-2:]))

    page.goto(f"{site}/projects/florist/")
    assert page.locator("#date").get_attribute("min") == msk_day

    page.goto(f"{site}/projects/cafe/")
    assert page.locator("#date").get_attribute("min") == msk_day
    ctx.close()
