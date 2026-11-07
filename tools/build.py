"""Сборка сайта для GitHub Pages.

    python tools/build.py [папка, по умолчанию _site] [--no-prerender] [--no-minify]

1. Копия сайта без бэкенда и служебных файлов.
2. Пререндер. То, что JavaScript дорисовывает в пустые контейнеры (меню, цены, карточки), записывается
   прямо в HTML: поисковик и браузер без JavaScript видят содержимое. Затем каждая страница открывается
   ещё раз, и контейнер откатывается, если скрипт его не перерисовал (кнопки остались бы без обработчиков),
   задвоил содержимое или страница начала падать с ошибкой.
3. Минификация CSS и JS — внешних файлов и блоков внутри страниц — через esbuild (нужен Node, в CI он есть).
4. Версия ?v=<хеш> в ссылках на CSS и JS: после обновления браузер не возьмёт старый файл из кэша.

Нужен Playwright: pip install playwright && python -m playwright install chromium
"""

import argparse
import functools
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", ".github", "backend", "tools", "node_modules", "_site", ".lh", "__pycache__", "_template"}
SKIP_FILES = {"render.yaml", ".gitignore", ".gitattributes"}
SKIP_SUFFIXES = {".md", ".py", ".pyc", ".toml"}
ESBUILD = "esbuild@0.24.0"

# ---------- 1. Копия ----------


def copy_site(out: Path) -> None:
    if out.exists():
        shutil.rmtree(out)

    def ignore(folder: str, names: list[str]) -> set[str]:
        rel = Path(folder).resolve().relative_to(ROOT)
        skip = {n for n in names if n in SKIP_DIRS or n in SKIP_FILES or Path(n).suffix in SKIP_SUFFIXES}
        if rel == Path("projects"):
            skip.add("cafe-bot")  # исходники бота на Python, сайт ссылается на них в GitHub
        return skip

    shutil.copytree(ROOT, out, ignore=ignore)
    (out / ".nojekyll").write_text("")


# ---------- 2. Пререндер ----------

SNAPSHOT_JS = """async () => {
  const SKIP = new Set(["SCRIPT", "STYLE", "TEMPLATE", "IFRAME", "INPUT", "TEXTAREA", "SELECT", "CANVAS", "svg"]);
  const src = await (await fetch(location.href, { cache: "no-store" })).text();
  const doc = new DOMParser().parseFromString(src, "text/html");
  const out = {};
  for (const el of doc.querySelectorAll("body [id]")) {
    if (SKIP.has(el.tagName) || el.innerHTML.trim()) continue;
    if (doc.querySelectorAll(`[id="${CSS.escape(el.id)}"]`).length !== 1) continue;
    const live = document.getElementById(el.id);
    // Закрытые окна и декоративные блоки поиску не нужны
    if (!live || live.closest("dialog:not([open]), [aria-hidden='true'], [hidden]")) continue;
    const clone = live.cloneNode(true);
    // Состояния анимаций и служебные элементы общих скриптов не сохраняем
    clone.querySelectorAll("*").forEach((n) => {
      n.classList.remove("reveal", "visible", "in", "loaded");
      if (n.getAttribute("class") === "") n.removeAttribute("class");
      n.removeAttribute("data-pf-note");
    });
    clone.querySelectorAll(".pf-demo-note, .pf-error").forEach((n) => n.remove());
    for (const child of clone.children) child.setAttribute("data-pre", "");
    const html = clone.innerHTML.trim();
    if (html && html.length < 300000) out[el.id] = { html, length: live.innerHTML.length, elements: clone.children.length };
  }
  return out;
}"""

VERIFY_JS = """(ids) => Object.fromEntries(ids.map((id) => {
  const el = document.getElementById(id);
  if (!el) return [id, { missing: true }];
  return [id, { stale: !!el.querySelector(":scope > [data-pre]"), length: el.innerHTML.length }];
}))"""


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass


class QuietServer(ThreadingHTTPServer):
    def handle_error(self, request, client_address) -> None:
        pass  # браузер закрывает соединения, когда страница уже загружена: это не ошибка сборки


def serve(folder: Path):
    handler = functools.partial(QuietHandler, directory=str(folder))
    httpd = QuietServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def fill(html: str, el_id: str, content: str) -> str | None:
    """Вставляет содержимое в пустой элемент с этим id. None — если такой элемент не найден ровно один раз."""
    pat = re.compile(r'(<([a-zA-Z][\w-]*)\b[^>]*\bid="' + re.escape(el_id) + r'"[^>]*>)\s*(</\2>)')
    found = pat.findall(html)
    if len(found) != 1:
        return None
    return pat.sub(lambda m: m.group(1) + content + m.group(3), html, count=1)


def open_page(browser, url: str):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, locale="ru-RU", timezone_id="Europe/Moscow")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(1200)
    return ctx, page, errors


def prerender(out: Path, pages: list[str]) -> dict:
    from playwright.sync_api import sync_playwright

    report = {}
    httpd, base = serve(out)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for rel in pages:
                path = out / rel
                url = f"{base}/{rel.removesuffix('index.html')}"
                ctx, page, errors_before = open_page(browser, url)
                snap = page.evaluate(SNAPSHOT_JS)
                ctx.close()

                original = path.read_text(encoding="utf-8")
                html, filled = original, {}
                for el_id, data in snap.items():
                    new = fill(html, el_id, data["html"])
                    if new is not None:
                        html, filled[el_id] = new, data
                if not filled:
                    report[rel] = {"filled": [], "rolled_back": {}}
                    continue
                path.write_text(html, encoding="utf-8")

                # Проверка: страница с готовым содержимым ведёт себя так же, как без него
                ctx, page, errors_after = open_page(browser, url)
                check = page.evaluate(VERIFY_JS, list(filled))
                ctx.close()
                rolled = {}
                if len(errors_after) > len(errors_before):
                    rolled = {i: f"ошибка на странице: {errors_after[-1][:80]}" for i in filled}
                else:
                    for el_id, data in filled.items():
                        c = check[el_id]
                        if c.get("missing"):
                            rolled[el_id] = "контейнер пропал"
                        elif c["stale"] and data["elements"]:
                            rolled[el_id] = "скрипт не перерисовал содержимое"
                        elif c["length"] > data["length"] * 1.6 + 200:
                            rolled[el_id] = "содержимое задвоилось"
                html = original
                for el_id, data in filled.items():
                    if el_id not in rolled:
                        html = fill(html, el_id, data["html"].replace(' data-pre=""', ""))
                path.write_text(html, encoding="utf-8")
                report[rel] = {"filled": [i for i in filled if i not in rolled], "rolled_back": rolled}
            browser.close()
    finally:
        httpd.shutdown()
    return report


# ---------- 3–4. Минификация и версии файлов ----------

INLINE = re.compile(r"(<(style|script)\b([^>]*)>)(.*?)(</\2>)", re.S)


def esbuild_cmd() -> list[str] | None:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    return [npx, "--yes", ESBUILD] if npx else None


def minify(out: Path) -> dict:
    cmd = esbuild_cmd()
    if not cmd:
        print("esbuild недоступен (нет Node): минификация пропущена")
        return {}
    before = after = 0
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        jobs: list[tuple[Path, Path]] = []  # (временный файл, откуда)
        blocks: dict[Path, list] = {}
        for f in sorted(out.rglob("*")):
            if f.suffix in {".css", ".js"} and ".min." not in f.name:
                jobs.append((f, f))
            elif f.suffix == ".html":
                html = f.read_text(encoding="utf-8")
                for n, m in enumerate(INLINE.finditer(html)):
                    tag, attrs, body = m.group(2), m.group(3), m.group(4)
                    # Внешние скрипты, JSON-LD и модули не трогаем
                    if not body.strip() or "src=" in attrs or ("type=" in attrs and "text/javascript" not in attrs):
                        continue
                    t = tmp / "inline" / f"{f.relative_to(out).as_posix().replace('/', '__')}__{n}.{'css' if tag == 'style' else 'js'}"
                    t.parent.mkdir(parents=True, exist_ok=True)
                    t.write_text(body, encoding="utf-8")
                    jobs.append((t, f))
                    blocks.setdefault(f, []).append((m.start(4), m.end(4), t))
        entries = [str(j[0]) for j in jobs]
        min_dir = tmp / "min"
        # Пачками: в Windows длина командной строки ограничена
        for i in range(0, len(entries), 60):
            batch = entries[i:i + 60]
            common = Path(min(batch)).anchor
            subprocess.run([*cmd, *batch, "--minify", "--charset=utf8", "--target=es2020", "--log-level=warning",
                            f"--outdir={min_dir}", f"--outbase={common}"], check=True, shell=sys.platform == "win32" and cmd[0].endswith(".cmd"))

        def minified(src: Path) -> Path:
            return min_dir / src.relative_to(Path(src.anchor))

        for src, origin in jobs:
            if src == origin:
                text_before, text_after = src.read_text(encoding="utf-8"), minified(src).read_text(encoding="utf-8")
                src.write_text(text_after, encoding="utf-8")
                before, after = before + len(text_before.encode()), after + len(text_after.encode())
        for f, items in blocks.items():
            html = f.read_text(encoding="utf-8")
            for start, end, t in sorted(items, reverse=True):
                body = minified(t).read_text(encoding="utf-8").strip()
                before, after = before + end - start, after + len(body)
                html = html[:start] + body + html[end:]
            f.write_text(html, encoding="utf-8")
    return {"before": before, "after": after}


LOCAL_ASSET = re.compile(r'\b(href|src)="((?![a-z]+:|//|#)[^"?#]+\.(?:css|js))"')


def version_assets(out: Path) -> int:
    count = 0

    def stamp(m: re.Match, folder: Path) -> str:
        nonlocal count
        target = (folder / m.group(2)).resolve()
        if not target.is_file():
            return m.group(0)
        count += 1
        return f'{m.group(1)}="{m.group(2)}?v={hashlib.sha256(target.read_bytes()).hexdigest()[:10]}"'

    for f in out.rglob("*.html"):
        html = f.read_text(encoding="utf-8")
        f.write_text(LOCAL_ASSET.sub(functools.partial(stamp, folder=f.parent), html), encoding="utf-8")
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", nargs="?", default="_site")
    ap.add_argument("--no-prerender", action="store_true")
    ap.add_argument("--no-minify", action="store_true")
    a = ap.parse_args()
    out = (ROOT / a.out).resolve()

    copy_site(out)
    print(f"Скопировано в {out}")

    if not a.no_prerender:
        demos = json.loads((ROOT / "projects" / "demos.json").read_text(encoding="utf-8"))["demos"]
        pages = ["index.html", *(f"projects/{d['slug']}/index.html" for d in demos)]
        report = prerender(out, pages)
        for rel, r in report.items():
            line = f"  {rel}: в HTML {len(r['filled'])}"
            if r["rolled_back"]:
                line += "; откатано: " + ", ".join(f"#{i} ({why})" for i, why in r["rolled_back"].items())
            print(line)
        (out / "prerender.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    if not a.no_minify:
        stats = minify(out)
        if stats:
            print(f"Минификация: {stats['before'] / 1024:.0f} КБ → {stats['after'] / 1024:.0f} КБ")
    print(f"Версии файлов проставлены: {version_assets(out)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
