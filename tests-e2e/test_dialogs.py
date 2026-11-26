"""A11Y-002: окна и шторки — фокус внутри, Tab не выходит наружу, Esc закрывает, фокус возвращается на кнопку."""

import pytest
from playwright.sync_api import expect

INSIDE = "(sel) => { const d = document.querySelector(sel); return !!d && d.contains(document.activeElement); }"
# (страница, кнопка открытия, окно, элементы, куда фокус тоже может попасть, закрывается ли по Esc)
CASES = [
    ("sushi", "#cartBtn", "#drawer", [], True),
    ("florist", "#cartBtn", "#drawer", [], True),
    ("realty", "[data-open], .obj, .card", "#modal", [], True),
    ("miniapp", "[data-open]", "#sheet", ["#mainBtn"], True),
]


@pytest.mark.parametrize("slug, opener, dialog, extra, esc", CASES, ids=[c[0] for c in CASES])
def test_dialog_keyboard(page, site, errors, slug, opener, dialog, extra, esc):
    page.goto(f"{site}/projects/{slug}/")
    if slug == "florist":
        expect(page.locator(dialog)).to_have_attribute("aria-hidden", "true")
        assert page.evaluate(f"() => document.querySelector('{dialog}').inert"), "закрытая корзина доступна с клавиатуры"
    button = page.locator(opener).first
    button.focus()
    button.press("Enter") if page.evaluate("() => document.activeElement.tagName") == "BUTTON" else button.click()
    expect(page.locator(dialog)).to_have_attribute("role", "dialog")
    page.wait_for_function(INSIDE, arg=dialog)
    for _ in range(25):
        page.keyboard.press("Tab")
        inside = page.evaluate(INSIDE, dialog) or any(page.evaluate(INSIDE, e) or page.evaluate(f"() => document.activeElement === document.querySelector('{e}')") for e in extra)
        assert inside, f"фокус ушёл за пределы окна: {page.evaluate('() => document.activeElement.outerHTML.slice(0, 80)')}"
    if esc:
        page.keyboard.press("Escape")
        page.wait_for_function(f"() => document.querySelector('{dialog}').inert")
        if page.evaluate("() => document.activeElement.tagName") != "BODY":
            assert page.evaluate(INSIDE, dialog) is False


def test_florist_cart_returns_focus(page, site, errors):
    page.goto(f"{site}/projects/florist/")
    page.locator("#cartBtn").focus()
    page.keyboard.press("Enter")
    page.wait_for_function(INSIDE, arg="#drawer")
    page.keyboard.press("Escape")
    page.wait_for_function("() => document.activeElement === document.getElementById('cartBtn')")


def test_bar_age_gate_is_modal(page, site, errors):
    page.goto(f"{site}/projects/bar/?gate")
    expect(page.locator("#gate")).to_be_visible()
    page.wait_for_function(INSIDE, arg="#gate")
    for _ in range(8):
        page.keyboard.press("Tab")
        assert page.evaluate(INSIDE, "#gate"), "до ответа на вопрос о возрасте фокус ушёл на сайт"
    page.locator("#gateYes").click()
    expect(page.locator("#gate")).to_be_hidden()


def test_kanban_keyboard(page, site, errors):
    # A11Y-003: карточку Taskly можно перенести в «Готово» без мыши
    page.goto(f"{site}/projects/saas/")
    task = page.locator(".col[data-col='todo'] .task").first
    title = task.get_attribute("data-title")
    task.focus()
    page.keyboard.press("ArrowRight")
    page.keyboard.press("ArrowRight")
    moved = page.locator(f".col[data-col='done'] .task[data-title='{title}']")
    expect(moved).to_have_count(1)
    expect(moved).to_be_focused()
    expect(page.locator("#boardLive")).to_contain_text("Готово")
    expect(page.locator(".confetti").first).to_be_attached()
    page.keyboard.press("ArrowUp")
    assert page.locator(".col[data-col='done'] .task").first.get_attribute("data-title") == title
