"""Сводка оценок Lighthouse: читает отчёты *.json из папки и печатает компактный JSON."""

import json
import sys
from datetime import date
from pathlib import Path

CATEGORIES = ["performance", "accessibility", "best-practices", "seo"]


def main(folder: str) -> None:
    pages = {}
    for report in sorted(Path(folder).glob("*.json")):
        try:
            lhr = json.loads(report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        cats = lhr.get("categories", {})
        scores = {c: round((cats.get(c, {}).get("score") or 0) * 100) for c in CATEGORIES}
        audits = lhr.get("audits", {})
        failed = [
            a["title"]
            for a in audits.values()
            if a.get("score") is not None and a["score"] < 0.9 and a.get("scoreDisplayMode") in ("binary", "numeric")
        ]
        pages[report.stem] = {"scores": scores, "lcp": audits.get("largest-contentful-paint", {}).get("displayValue"), "issues": failed[:12]}
    print(json.dumps({"date": date.today().isoformat(), "pages": pages}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".lh")
