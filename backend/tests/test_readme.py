"""DOC-002: таблица API в backend/README.md совпадает с маршрутами приложения — в обе стороны."""

import re
from pathlib import Path

import pytest

from app.main import app

README = Path(__file__).resolve().parents[1] / "README.md"


def norm(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path.split("?")[0])


def documented() -> tuple[set[str], set[str]]:
    """Пути из таблицы API и префиксы вида `/api/v1/admin/catalog/...`."""
    paths, prefixes = set(), set()
    for line in README.read_text(encoding="utf-8").splitlines():
        if not re.match(r"\| [A-Z/]+ \| `", line):
            continue
        tokens = re.findall(r"`([^`]+)`", line.split("|")[2])
        base = norm(tokens[0])
        for t in tokens:
            # Короткая запись `/bookings/{id}` — соседний путь: подставляем вместо хвоста первого пути
            options = [t] if t.startswith(("/api", "/health")) else [
                base.rsplit("/", k)[0] + t for k in range(1, base.count("/") + 1)]
            full = next((o for o in options if norm(o) in routes()), options[0])
            if full.endswith("..."):
                prefixes.add(norm(full.removesuffix("...")))
            else:
                paths.add(norm(full))
    return paths, prefixes


def routes() -> set[str]:
    return {norm(p) for p in app.openapi()["paths"]}  # схема OpenAPI строится и при выключенном /docs


def test_every_documented_path_exists():
    paths, prefixes = documented()
    assert paths, "таблица API не найдена"
    missing = sorted(p for p in paths if p not in routes())
    assert not missing, f"В README есть пути, которых нет в API: {missing}"
    assert all(any(r.startswith(p) for r in routes()) for p in prefixes)


@pytest.mark.parametrize("route", sorted(routes()))
def test_every_route_is_documented(route):
    paths, prefixes = documented()
    assert route in paths or any(route.startswith(p) for p in prefixes), f"{route} нет в таблице API backend/README.md"
