"""Сборка для Pages публикует только сайт: без архивов, кешей, бэкенда и служебных файлов (CI-001, REPO-001).

    pip install pytest && pytest tools/test_build.py
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build


def published(tmp_path: Path) -> set[str]:
    out = tmp_path / "_site"
    build.copy_site(out)
    return {p.relative_to(out).as_posix() for p in out.rglob("*")}


def test_only_site_files_are_published(tmp_path):
    files = published(tmp_path)
    assert "index.html" in files
    assert "admin/index.html" in files
    assert "projects/shared/api.js" in files
    assert "projects/cafe/index.html" in files
    assert ".nojekyll" in files

    leaked = sorted(
        f for f in files
        if f != ".nojekyll" and (
            any(part.startswith(".") for part in f.split("/"))
            or f.endswith((".zip", ".md", ".py", ".pyc", ".toml", ".yml", ".yaml"))
            or f.split("/")[0] in {"backend", "tools", "_site", "node_modules"}
            or f in {"LICENSE", "projects/demos.json"}
            or f.startswith(("projects/cafe-bot", "projects/_template"))
        )
    )
    assert not leaked, f"В публикацию попали служебные файлы: {leaked[:10]}"


def test_unknown_root_files_are_not_published(tmp_path, monkeypatch):
    # Любой новый файл в корне (архив, отчёт, кеш) не уезжает на Pages, пока его не добавят в белый список
    root = tmp_path / "repo"
    for name in build.ROOT_FILES:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text("x", encoding="utf-8")
    for name in build.ROOT_DIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
        (root / name / "page.html").write_text("x", encoding="utf-8")
    (root / "Проект.zip").write_bytes(b"PK")
    (root / "secret.txt").write_text("x", encoding="utf-8")
    (root / ".claude").mkdir()
    (root / ".claude" / "launch.json").write_text("{}", encoding="utf-8")
    (root / "projects" / "archive.zip").write_bytes(b"PK")
    monkeypatch.setattr(build, "ROOT", root)

    files = published(tmp_path)
    assert "Проект.zip" not in files
    assert "secret.txt" not in files
    assert not any(f.startswith(".claude") for f in files)
    assert "projects/archive.zip" not in files
    assert "projects/page.html" in files


def test_whitelisted_root_files_exist():
    missing = [n for n in (*build.ROOT_FILES, *build.ROOT_DIRS) if not (build.ROOT / n).exists()]
    assert not missing, f"В белом списке сборки есть несуществующие пути: {missing}"


def test_dynamic_offers_js_is_versioned(tmp_path):
    # FE-001: api.js подключает offers.js сам, и без версии браузер держал старые цены в кэше
    out = tmp_path / "_site"
    build.copy_site(out)
    build.version_dynamic_assets(out)
    build.version_assets(out)
    api_js = (out / "projects" / "shared" / "api.js").read_text(encoding="utf-8")
    assert '"offers.js?v=' in api_js
    html = (out / "projects" / "cafe" / "index.html").read_text(encoding="utf-8")
    assert "shared/api.js?v=" in html


def test_sitemap_gets_lastmod(tmp_path):
    # SEO-001: у адресов sitemap — дата последнего изменения страницы
    out = tmp_path / "_site"
    build.copy_site(out)
    assert build.add_lastmod(out) > 0
    xml = (out / "sitemap.xml").read_text(encoding="utf-8")
    assert re.search(r"/projects/cafe/</loc><lastmod>\d{4}-\d\d-\d\d</lastmod>", xml)
