"""Демо-сайты портфолио: проверка и создание.

Каждое демо упоминается в нескольких местах: карточка на главной, цена «такого же», список для поиска
без JavaScript, sitemap, скриншоты, README и правила на сервере. Раньше это держалось на памяти,
теперь — на этом скрипте.

    python tools/demos.py check                      проверить все демо (запускается в CI)
    python tools/demos.py new <slug> "<Название>" --niche "Кофейня" --type site --opts booking,tg
                                                     создать демо из projects/_template и прописать везде
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"
REGISTRY = PROJECTS / "demos.json"
NOT_DEMOS = {"shared", "cafe-bot", "_template"}


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    (ROOT / rel).write_text(text, encoding="utf-8", newline="\n")


def registry() -> list[dict]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["demos"]


def js_key(slug: str) -> str:
    """Ключ объекта в JS: coffee без кавычек, coffee-bar в кавычках."""
    return slug if slug.isidentifier() else json.dumps(slug)


# Где должно встречаться демо и как его там узнать
PLACES = {
    "карточка на главной (script.js)": ("script.js", lambda s: f'slug: "{s}"'),
    "цена «такого же» (projects/shared/offers.js)": ("projects/shared/offers.js", lambda s: f"{js_key(s)}: {{ type:"),
    "список работ без JavaScript (index.html)": ("index.html", lambda s: f'href="projects/{s}/"'),
    "sitemap.xml": ("sitemap.xml", lambda s: f"/projects/{s}/</loc>"),
    "таблица в README.md": ("README.md", lambda s: f"/projects/{s}/)"),
    "правила на сервере (backend/app/sites.py)": ("backend/app/sites.py", lambda s: f'Site("{s}"'),
    "копия правил в демо-клиенте (api.js)": ("projects/shared/api.js", lambda s: f'{{"slug": "{s}"'),
}

# Чего не должно быть на страницах демо
FORBIDDEN = {
    "+7 (900) 000-00-00": "телефон-заглушка: у каждого демо свой номер",
    "ул. Примерная": "адрес-заглушка: адреса в Петербурге",
    'class="demo-bar"': "верхняя плашка демо больше не нужна: её заменила кнопка внизу",
    "{{": "не заполнен шаблон",
}
REQUIRED = {
    '<html lang="ru">': "язык страницы",
    'name="viewport"': "мета viewport для телефонов",
    'name="description"': "описание для поиска",
    "<title>": "заголовок страницы",
    "../shared/api.js": "клиент API: формы, кнопка «Хочу такой сайт», уведомление администратору",
    "<footer": "подвал с подписью о вымышленных данных",
}


def check() -> int:
    problems = []
    slugs = [d["slug"] for d in registry()]
    dirs = sorted(p.name for p in PROJECTS.iterdir() if p.is_dir() and p.name not in NOT_DEMOS)
    for name in sorted(set(dirs) - set(slugs)):
        problems.append(f"projects/{name}/ нет в projects/demos.json")
    for name in sorted(set(slugs) - set(dirs)):
        problems.append(f"{name} есть в projects/demos.json, но папки projects/{name}/ нет")
    shots = read("tools/screenshots.py")
    if "demos.json" not in shots:
        problems.append("tools/screenshots.py должен брать список демо из projects/demos.json")

    texts = {rel: read(rel) for rel, _ in PLACES.values()}
    for slug in slugs:
        for place, (rel, needle) in PLACES.items():
            if needle(slug) not in texts[rel]:
                problems.append(f"{slug}: нет в месте «{place}»")
        page = PROJECTS / slug / "index.html"
        if not page.exists():
            continue
        html = page.read_text(encoding="utf-8")
        for needle, why in REQUIRED.items():
            if needle not in html:
                problems.append(f"{slug}: нет {needle!r} ({why})")
        for needle, why in FORBIDDEN.items():
            if needle in html:
                problems.append(f"{slug}: найдено {needle!r} — {why}")

    if problems:
        print("Проблемы с демо-сайтами:")
        print("\n".join(f"  - {p}" for p in problems))
        return 1
    print(f"Все {len(slugs)} демо на месте и прописаны везде")
    return 0


def insert_before(rel: str, anchor: str, text: str) -> None:
    src = read(rel)
    if src.count(anchor) != 1:
        sys.exit(f"Не нашёл, куда вставить в {rel}: ожидалась ровно одна строка «{anchor.strip()[:60]}»")
    write(rel, src.replace(anchor, text + anchor, 1))


def new(slug: str, title: str, niche: str, kind: str, opts: list[str]) -> int:
    if not re.fullmatch(r"[a-z][a-z0-9-]{1,30}", slug):
        sys.exit("slug: латиница, цифры и дефис, например coffee-bar")
    if slug in NOT_DEMOS or (PROJECTS / slug).exists():
        sys.exit(f"projects/{slug}/ уже есть")
    q = lambda v: json.dumps(v, ensure_ascii=False)  # noqa: E731

    target = PROJECTS / slug
    shutil.copytree(PROJECTS / "_template", target)
    page = target / "index.html"
    html = page.read_text(encoding="utf-8")
    html = html.replace('  <meta name="robots" content="noindex">\n', "")
    html = re.sub(r"  <!-- Заготовка демо-сайта.*?-->\n", "", html)
    html = html.replace("{{SLUG}}", slug).replace("{{TITLE}}", title).replace("{{NICHE}}", niche)
    page.write_text(html, encoding="utf-8", newline="\n")

    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    data["demos"].append({"slug": slug, "title": title, "niche": niche})
    REGISTRY.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    opts_js = ", ".join(q(o) for o in opts)
    insert_before("projects/shared/offers.js", '    "cafe-bot": {', f"    {js_key(slug)}: {{ type: {q(kind)}, opts: [{opts_js}] }},\n")
    insert_before("script.js", '  { slug: "admin",', (
        f'  {{ slug: {q(slug)}, title: {q(title)}, niche: {q(niche)},\n'
        f'    task: "Задача бизнеса одним предложением.",\n'
        f'    can: "Что умеет сайт одним-двумя предложениями.",\n'
        f'    chips: ["Польза 1", "Польза 2"],\n'
        f'    text: "Короткое описание для окна кейса.",\n'
        f'    goal: "Задача бизнеса подробнее.",\n'
        f'    done: ["Что сделано"],\n'
        f'    tech: ["Как устроено"] }},\n'))
    insert_before("index.html", '            <li><a href="admin/">', f'            <li><a href="projects/{slug}/">{title} — {niche.lower()}</a></li>\n')
    insert_before("sitemap.xml", "  <url><loc>https://feyegetsu.github.io/portfolio/privacy.html</loc></url>",
                  f"  <url><loc>https://feyegetsu.github.io/portfolio/projects/{slug}/</loc></url>\n")
    insert_before("README.md", "| 🤖 | [**Бот для заказов**]",
                  f'| <img src="assets/previews/{slug}.jpg" width="160"> | [**{title}**](https://feyegetsu.github.io/portfolio/projects/{slug}/) | {niche} | Ключевая фишка |\n')
    insert_before("backend/app/sites.py", "    ]\n}", f"        Site({q(slug)}, {q(title)}, leads=True),\n")

    # Копия правил в демо-клиенте обновляется из sites.py
    r = subprocess.run([sys.executable, "-m", "app.rules_export"], cwd=ROOT / "backend", capture_output=True, text=True)
    regen = "обновлена" if r.returncode == 0 else "НЕ обновлена: запустите cd backend && python -m app.rules_export"

    print(f"""Готово: projects/{slug}/index.html
Прописано: demos.json, offers.js, карточка в script.js, список без JS, sitemap.xml, README, backend/app/sites.py
Копия правил в api.js {regen}.

Дальше:
  1. Сверстайте страницу: projects/{slug}/index.html
  2. Заполните карточку в script.js: task, can, chips, goal, done, tech
  3. Нужна запись по времени или заказы — допишите правила в backend/app/sites.py и перегенерируйте копию
  4. python tools/demos.py check""")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check", help="проверить все демо")
    n = sub.add_parser("new", help="создать демо из шаблона")
    n.add_argument("slug")
    n.add_argument("title")
    n.add_argument("--niche", default="Услуги")
    n.add_argument("--type", default="site", choices=["landing", "site", "shop", "bot", "botpro", "miniapp"])
    n.add_argument("--opts", default="tg", help="допы через запятую: booking, calc, tg, bot, admin, texts")
    a = ap.parse_args()
    if a.cmd == "check":
        return check()
    return new(a.slug, a.title, a.niche, a.type, [o.strip() for o in a.opts.split(",") if o.strip()])


if __name__ == "__main__":
    sys.exit(main())
