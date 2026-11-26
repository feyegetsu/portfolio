"""SEO-002: пререндер сборки не запекает в HTML содержимое, зависящее от даты (data-no-prerender).

Сборка идёт отдельным процессом, как в CI: свой Playwright внутри теста конфликтовал бы с Playwright pytest.
"""

import json
import re
import subprocess
import sys

from conftest import ROOT

DATED = ("cafe", "restaurant", "gastrobar", "fitness", "bar", "barbershop")


def test_dated_containers_are_not_prerendered(tmp_path):
    out = tmp_path / "_site"
    subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), str(out), "--no-minify"], check=True, capture_output=True)
    report = json.loads((out / "prerender.json").read_text(encoding="utf-8"))
    for slug in DATED:
        rel = f"projects/{slug}/index.html"
        dated = set(re.findall(r'id="([\w-]+)" data-no-prerender', (ROOT / rel).read_text(encoding="utf-8")))
        assert dated, rel
        baked = dated & set(report[rel]["filled"])
        assert not baked, f"{rel}: запечены {baked}"
    assert any(r["filled"] for r in report.values())  # остальное по-прежнему пререндерится
