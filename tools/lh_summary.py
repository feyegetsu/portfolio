"""Сводка оценок Lighthouse.

    python tools/lh_summary.py .lh                      печатает JSON со сводкой
    python tools/lh_summary.py .lh --readme README.md   ещё и обновляет таблицу в README
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

CATEGORIES = ["performance", "accessibility", "best-practices", "seo"]
TITLES = {
    "home-mobile": "Главная (телефон)", "home-desktop": "Главная (компьютер)", "miniapp": "Mini App",
    "florist": "Пион & Ко", "dental": "Белая линия", "cafe": "Зерно", "barbershop": "BLADE",
    "fitness": "PULSE", "autoservice": "МоторЛайн", "realty": "Квадрат", "saas": "Taskly",
}


def collect(folder: str) -> dict:
    pages = {}
    for report in sorted(Path(folder).glob("*.json")):
        try:
            lhr = json.loads(report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cats = lhr.get("categories", {})
        if not cats:
            continue
        audits = lhr.get("audits", {})
        failed = [
            a["title"]
            for a in audits.values()
            if a.get("score") is not None and a["score"] < 0.9 and a.get("scoreDisplayMode") in ("binary", "numeric")
        ]
        # Для проблем доступности сохраняем, на каких элементах они найдены
        a11y_ids = [r["id"] for r in cats.get("accessibility", {}).get("auditRefs", [])]
        elements = {}
        for aid in a11y_ids:
            audit = audits.get(aid, {})
            if audit.get("score") == 0:
                items = (audit.get("details") or {}).get("items") or []
                elements[aid] = [(i.get("node") or {}).get("snippet", "")[:140] for i in items[:4]]
        pages[report.stem] = {
            "scores": {c: round((cats.get(c, {}).get("score") or 0) * 100) for c in CATEGORIES},
            "lcp": audits.get("largest-contentful-paint", {}).get("displayValue"),
            "cls": audits.get("cumulative-layout-shift", {}).get("displayValue"),
            "issues": failed[:12],
            "a11y": elements,
        }
    return {"date": date.today().isoformat(), "pages": pages}


def badge(score: int) -> str:
    return f"{'🟢' if score >= 90 else '🟠' if score >= 50 else '🔴'} {score}"


def table(summary: dict) -> str:
    order = list(TITLES)
    rows = sorted(summary["pages"].items(), key=lambda kv: order.index(kv[0]) if kv[0] in order else 99)
    lines = [
        f"Замер от {summary['date']}. Страницы без пометки измерены в мобильном режиме (медленный 4G, слабый процессор).",
        "",
        "| Страница | Скорость | Доступность | Практики | SEO | LCP |",
        "|---|---|---|---|---|---|",
    ]
    for key, page in rows:
        s = page["scores"]
        lines.append(
            f"| {TITLES.get(key, key)} | {badge(s['performance'])} | {badge(s['accessibility'])} | "
            f"{badge(s['best-practices'])} | {badge(s['seo'])} | {page['lcp'] or '—'} |"
        )
    return "\n".join(lines)


def update_readme(path: str, summary: dict) -> None:
    readme = Path(path)
    text = readme.read_text(encoding="utf-8")
    block = f"<!-- LIGHTHOUSE:START -->\n{table(summary)}\n<!-- LIGHTHOUSE:END -->"
    readme.write_text(re.sub(r"<!-- LIGHTHOUSE:START -->.*?<!-- LIGHTHOUSE:END -->", block, text, flags=re.S), encoding="utf-8")


def main() -> None:
    args = sys.argv[1:]
    folder = args[0] if args and not args[0].startswith("--") else ".lh"
    summary = collect(folder)
    if "--readme" in args:
        update_readme(args[args.index("--readme") + 1], summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
