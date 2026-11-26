"""SEO-002: пререндер сборки не запекает в HTML содержимое, зависящее от даты (data-no-prerender)."""

import re
import sys

from conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import build


def test_dated_containers_are_not_prerendered(tmp_path):
    out = tmp_path / "_site"
    build.copy_site(out)
    pages = [f"projects/{s}/index.html" for s in ("cafe", "restaurant", "gastrobar", "fitness", "bar", "barbershop")]
    report = build.prerender(out, pages)
    for rel in pages:
        html = (ROOT / rel).read_text(encoding="utf-8")
        dated = set(re.findall(r'id="([\w-]+)" data-no-prerender', html))
        assert dated, rel
        assert not dated & set(report[rel]["filled"]), f"{rel}: запечены {dated & set(report[rel]['filled'])}"
    assert any(r["filled"] for r in report.values())  # остальное по-прежнему пререндерится
