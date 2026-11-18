"""SEC-005: подключение к API по ?api= — только https, только в этой вкладке, с плашкой; ответы API не исполняются как HTML."""

import json

from playwright.sync_api import expect

FAKE = "http://127.0.0.1:9"  # «свой компьютер»: подключается без вопроса, а ответы подменяем через page.route
EVIL_PRICE = '<img src=x onerror="window.__xss=1">'


def fake_api(page, catalog_price=EVIL_PRICE):
    def handle(route):
        url = route.request.url
        if url.endswith("/api/v1/sites/miniapp/catalog"):
            body = [{"id": 1, "site": "miniapp", "ref": "1", "name": "Маргарита", "category": "Пицца", "price": catalog_price, "active": True}]
            return route.fulfill(status=200, content_type="application/json", body=json.dumps(body))
        return route.fulfill(status=404, content_type="application/json", body='{"detail": "Не найдено"}')

    page.route(f"{FAKE}/**", handle)


def test_malicious_catalog_price_is_not_executed(page, site):
    fake_api(page)
    page.goto(f"{site}/projects/miniapp/?api={FAKE}")
    assert page.evaluate("() => PortfolioAPI.mode") == "remote"
    page.wait_for_timeout(800)
    assert page.evaluate("() => window.__xss") is None
    assert page.locator("img[src='x']").count() == 0


def test_plain_http_api_is_refused(page, site):
    dialogs = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    page.goto(f"{site}/projects/cafe/?api=http://example.com")
    assert page.evaluate("() => PortfolioAPI.mode") == "demo"
    assert dialogs == []  # даже не спрашиваем: пароль ушёл бы открытым текстом


def test_foreign_https_api_needs_confirm_and_lives_in_one_tab(page, site, context):
    messages = []
    page.on("dialog", lambda d: (messages.append(d.message), d.accept()))
    page.route("https://other.example/**", lambda r: r.fulfill(status=200, content_type="application/json", body="[]"))
    page.goto(f"{site}/projects/cafe/?api=https://other.example")
    assert page.evaluate("() => PortfolioAPI.mode") == "remote"
    assert "https://other.example" in messages[0]  # в вопросе полный адрес
    expect(page.locator(".pf-remote")).to_contain_text("other.example")

    page.goto(f"{site}/projects/cafe/")  # та же вкладка: адрес помнится до её закрытия
    assert page.evaluate("() => PortfolioAPI.mode") == "remote"

    other = context.new_page()  # новая вкладка — снова демо
    other.goto(f"{site}/projects/cafe/")
    assert other.evaluate("() => PortfolioAPI.mode") == "demo"

    page.locator(".pf-remote a").click()  # «Отключить»
    page.wait_for_url("**api=off**")
    assert page.evaluate("() => PortfolioAPI.mode") == "demo"


def test_declined_confirm_keeps_demo(page, site):
    page.on("dialog", lambda d: d.dismiss())
    page.goto(f"{site}/projects/cafe/?api=https://evil.example")
    assert page.evaluate("() => PortfolioAPI.mode") == "demo"
