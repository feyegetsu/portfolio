"""Базовые сценарии: заявка, запись, заказ и каталог проходят от сайта до админки (демо-режим и настоящий API)."""

import json
import re
import urllib.parse
import urllib.request

from conftest import OWNER, demo_login
from playwright.sync_api import expect


def test_cafe_lead_appears_in_admin(page, site, errors):
    page.goto(f"{site}/projects/cafe/")
    form = page.locator("#form")
    form.locator("[name=name]").fill("Е2Е Анна")
    form.locator("[name=phone]").fill("+7 900 123-45-67")
    form.locator("button[type=submit], button:not([type])").last.click()
    expect(page.locator("#success")).to_be_visible()

    page.goto(f"{site}/admin/#leads")
    page.locator("#loginForm [name=email]").fill("demo@feyegetsu.dev")
    page.locator("#loginForm [name=password]").fill("demo")
    page.locator("#loginForm button[type=submit]").click()
    page.locator("[data-view=leads]").click()
    expect(page.locator("#content")).to_contain_text("Е2Е Анна")


def test_barbershop_booking_blocks_slot(page, site, errors):
    page.goto(f"{site}/projects/barbershop/")
    day = page.evaluate("() => PortfolioAPI.siteToday('barbershop', 1)")
    page.evaluate("""(day) => PortfolioAPI.createBooking('barbershop', {
        resource: 'Артём', service: 'Стрижка', starts_at: `${day}T15:00:00`, name: 'Занял', phone: '+79001234567' })""", day)
    page.reload()
    page.locator("#optServices .opt").first.click()
    page.locator(".step[data-step='0'] [data-next]").click()
    page.locator("#optMasters .opt", has_text="Артём").click()
    page.locator(".step[data-step='1'] [data-next]").click()
    page.locator("#days .day").nth(1).click()
    slot = page.locator("#times .time", has_text="15:00")
    expect(slot).to_be_disabled()
    expect(page.locator("#times .time", has_text="16:00")).to_be_enabled()


def test_admin_price_change_shows_on_sushi(page, site, errors):
    page.goto(f"{site}/projects/sushi/")
    demo_login(page, site)
    page.evaluate("""async () => {
        const item = (await PortfolioAPI.admin.catalog({ site: 'sushi' })).find((c) => c.ref === 's4');
        await PortfolioAPI.admin.updateCatalog(item.id, { price: 777 });
    }""")
    page.reload()
    expect(page.locator("body")).to_contain_text("777")


def test_miniapp_order_moves_through_statuses(page, site, errors):
    page.clock.install()
    page.goto(f"{site}/projects/miniapp/")
    page.locator("[data-plus='5']").first.click()  # бургер без размеров
    page.locator("#mainBtn").click()               # корзина
    page.locator("[data-mode='pickup']").first.click()
    page.locator("#mainBtn").click()               # оформление
    page.locator("#checkoutForm [name=name]").fill("Е2Е Никита")
    page.locator("#checkoutForm [name=phone]").fill("+79001234567")
    page.locator("#mainBtn").click()
    expect(page.locator(".status h2")).to_contain_text("Заказ №")
    expect(page.locator(".tstep.now")).to_contain_text("Заказ принят")
    page.clock.run_for(15_000)  # «кухня» в демо двигает заказ раз в 6 секунд, экран опрашивает раз в 2
    expect(page.locator(".tstep.now, .tstep.done").last).not_to_contain_text("Заказ принят")


def test_remote_mode_lead_reaches_real_api(page, site, api, errors):
    page.goto(f"{site}/projects/cafe/?api={api}")
    assert page.evaluate("() => PortfolioAPI.mode") == "remote"
    form = page.locator("#form")
    form.locator("[name=name]").fill("Е2Е Удалённая")
    form.locator("[name=phone]").fill("+79001234567")
    form.locator("button[type=submit], button:not([type])").last.click()
    expect(page.locator("#success")).to_be_visible()

    token = json.load(urllib.request.urlopen(urllib.request.Request(
        f"{api}/api/v1/auth/login", data=json.dumps({"email": OWNER[0], "password": OWNER[1]}).encode(),
        headers={"Content-Type": "application/json"})))["access_token"]
    leads = json.load(urllib.request.urlopen(urllib.request.Request(
        f"{api}/api/v1/admin/leads?q={urllib.parse.quote('удалённая')}", headers={"Authorization": f"Bearer {token}"})))
    assert leads["total"] == 1


def test_item_added_in_admin_appears_on_storefront(page, site, errors):
    # BUG-011: форма «Добавить» в админке раньше ничего не меняла на витрине
    page.goto(f"{site}/projects/sushi/")
    demo_login(page, site)
    page.evaluate("""async () => {
        await PortfolioAPI.admin.addCatalog('sushi', { ref: 'custom-1', name: 'Ролл <b>Е2Е</b>', category: 'Роллы', price: 555 });
        await PortfolioAPI.admin.addCatalog('florist', { ref: 'custom-2', name: 'Букет Е2Е', category: 'Сезонные', price: 4321 });
        const s4 = (await PortfolioAPI.admin.catalog({ site: 'sushi' })).find((c) => c.ref === 's4');
        await PortfolioAPI.admin.deleteCatalog(s4.id);
    }""")
    page.reload()
    expect(page.locator("#menuBody")).to_contain_text("Ролл <b>Е2Е</b>")  # название — текстом, без разметки
    expect(page.locator("#menuBody")).to_contain_text("555")
    expect(page.locator("#menuBody h3", has_text=re.compile("^Филадельфия$"))).to_have_count(0)  # удалённое пропало
    page.locator("[data-inc='custom-1']").click()
    page.goto(f"{site}/projects/florist/")
    expect(page.locator("#grid")).to_contain_text("Букет Е2Е")
    expect(page.locator("#filters")).to_contain_text("Сезонные")


def test_first_visit_theme_follows_system(browser, site):
    # FE-002: при пустом localStorage тема берётся из настроек системы, выбор пользователя важнее
    ctx = browser.new_context(color_scheme="dark")
    page = ctx.new_page()
    for path in ("", "admin/", "privacy.html"):
        page.goto(f"{site}/{path}")
        assert page.evaluate("() => document.documentElement.dataset.theme") == "dark", path
    page.evaluate("() => localStorage.setItem('theme', 'light')")
    page.reload()
    assert page.evaluate("() => document.documentElement.dataset.theme") == "light"
    ctx.close()
