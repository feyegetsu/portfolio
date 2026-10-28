"""Скриншоты демо-проектов для карточек портфолио, README и OG-картинки.

Запуск (сайт должен раздаваться локально):
    python -m http.server 8000 &
    python tools/screenshots.py http://localhost:8000
"""

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
OUT = Path(__file__).resolve().parent.parent / "assets" / "previews"

DEMOS = ["miniapp", "florist", "dental", "cafe", "barbershop", "fitness", "autoservice", "realty", "saas"]


def settle(page):
    """Ждём шрифты, фото и анимации появления."""
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(2200)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 800}, color_scheme="light", locale="ru-RU")
        page = ctx.new_page()

        for slug in DEMOS:
            page.goto(f"{BASE}/projects/{slug}/")
            settle(page)
            page.screenshot(path=OUT / f"{slug}.jpg", type="jpeg", quality=72)
            print("ok", slug)

        # OG-картинка: первый экран главной в формате 1200×630
        page.set_viewport_size({"width": 1200, "height": 630})
        page.goto(f"{BASE}/")
        settle(page)
        page.screenshot(path=OUT.parent / "og-image.jpg", type="jpeg", quality=85)
        print("ok og-image")

        # Широкий кадр главной для README
        page.set_viewport_size({"width": 1440, "height": 900})
        page.goto(f"{BASE}/")
        settle(page)
        page.screenshot(path=OUT.parent / "hero.jpg", type="jpeg", quality=80)
        print("ok hero")

        # Мобильные кадры для README
        mobile = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True, locale="ru-RU")
        m = mobile.new_page()
        for slug in ["miniapp", "florist", "realty"]:
            m.goto(f"{BASE}/projects/{slug}/" + ("?embed" if slug == "miniapp" else ""))
            settle(m)
            m.screenshot(path=OUT / f"{slug}-mobile.jpg", type="jpeg", quality=70)
            print("ok", slug, "mobile")

        browser.close()


if __name__ == "__main__":
    main()
