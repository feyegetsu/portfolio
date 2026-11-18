"""Доступность: axe-core на всех страницах (A11Y-001 — контраст текста)."""

import json

import pytest
from axe_playwright_python.sync_playwright import Axe
from conftest import ROOT

DEMOS = [d["slug"] for d in json.loads((ROOT / "projects" / "demos.json").read_text(encoding="utf-8"))["demos"]]
PAGES = ["", "privacy.html", "admin/", *(f"projects/{s}/" for s in DEMOS)]
axe = Axe()


def serious(results, only: set[str] | None = None) -> list[str]:
    out = []
    for v in results.response["violations"]:
        if v["impact"] in ("serious", "critical") and (only is None or v["id"] in only):
            targets = ", ".join(" ".join(n["target"]) for n in v["nodes"][:3])
            out.append(f"{v['id']} ({v['impact']}, {len(v['nodes'])}): {targets}")
    return out


def audit(page, site, path):
    page.emulate_media(reduced_motion="reduce")  # без анимаций: проверяем итоговые цвета, а не кадры перехода
    page.goto(f"{site}/{path}", wait_until="networkidle")
    page.wait_for_timeout(500)
    # Анимации появления (reveal) прячут блоки до прокрутки: показываем всё, как увидит пользователь
    page.evaluate("""() => document.querySelectorAll('[data-reveal], .reveal').forEach((el) => el.classList.add('in', 'visible', 'shown'))""")
    page.wait_for_timeout(1500)
    return axe.run(page)


@pytest.mark.parametrize("path", PAGES)
def test_color_contrast(page, site, path):
    problems = serious(audit(page, site, path), {"color-contrast"})
    assert not problems, "\n".join(problems)
