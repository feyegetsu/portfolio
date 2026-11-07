"""Правила сайтов и каталоги для демо-режима в браузере.

Источник правды один: sites.py (часы, сетка, вместимость, цены доставки, размеры, промокоды) и seed.py (каталоги).
Демо-клиент projects/shared/api.js получает их копию между маркерами RULES:START и RULES:END,
сгенерированную этим модулем. Тест test_rules_sync падает, если копия устарела.

Обновить копию после правки правил:
    cd backend && python -m app.rules_export
"""

import json
import sys
from pathlib import Path

from .seed import CATALOGS
from .sites import SITES, Pricing, Site

START = "/* RULES:START"
END = "/* RULES:END */"
API_JS = Path(__file__).resolve().parents[2] / "projects" / "shared" / "api.js"


def _pricing(p: Pricing) -> dict:
    return {
        "delivery": p.delivery,
        "freeFrom": p.free_from,
        "sized": sorted(p.sized_categories),
        "sizes": [list(s) for s in p.sizes],
        "extras": [list(e) for e in p.extras],
        "promos": dict(p.promos),
    }


def _site(s: Site) -> dict:
    d = {
        "slug": s.slug, "name": s.name,
        "leads": s.leads, "bookings": s.bookings, "exclusive": s.exclusive_slots, "orders": s.orders, "catalog": s.catalog,
        "tz": s.tz, "step": s.step_minutes, "hours": list(s.hours), "horizon": s.horizon_days,
        "resources": s.resources, "capacity": s.slot_capacity,
    }
    if s.pricing:
        d["pricing"] = _pricing(s.pricing)
    return d


def render() -> str:
    """Блок кода для api.js: константы SITES и CATALOGS."""
    dump = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731
    lines = [
        f"  {START} — сгенерировано из backend/app/sites.py и seed.py командой `python -m app.rules_export`, руками не править */",
        "  const SITES = [",
        *(f"    {dump(_site(s))}," for s in SITES.values()),
        "  ];",
        "  // Каталоги, которыми управляют из админки; ref совпадает с id позиции на сайте",
        "  const CATALOGS = {",
        *(f"    {slug}: {dump([list(i) for i in items])}," for slug, items in CATALOGS.items()),
        "  };",
        f"  {END}",
    ]
    return "\n".join(lines)


def extract(text: str) -> str:
    """Текущий сгенерированный блок в api.js, от строки с START до строки с END."""
    start = text.rindex("\n", 0, text.index(START)) + 1
    end = text.index(END) + len(END)
    return text[start:end]


def write(path: Path = API_JS) -> bool:
    text = path.read_text(encoding="utf-8")
    new = text.replace(extract(text), render())
    if new == text:
        return False
    path.write_text(new, encoding="utf-8", newline="\n")
    return True


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else API_JS
    print("Обновлено:" if write(target) else "Уже актуально:", target)
