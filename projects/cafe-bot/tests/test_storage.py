"""BOT-003: импорт не создаёт файлов, база — по DB_PATH или рядом с bot.py, корзина переживает перезапуск."""

import importlib
from pathlib import Path

import bot as cafe


def test_import_creates_no_files(tmp_path):
    before = set(tmp_path.iterdir())
    importlib.reload(cafe)
    assert set(tmp_path.iterdir()) == before  # тесты идут из tmp_path (tmp_cwd), cafe.db там не появился


def test_db_path():
    assert cafe.db_path({}) == Path(cafe.__file__).resolve().parent / "cafe.db"
    assert cafe.db_path({"DB_PATH": "/data/cafe.db"}) == Path("/data/cafe.db")


async def test_cart_survives_restart(tmp_path):
    path = tmp_path / "cafe.db"
    first = cafe.Storage(path)
    await first.add_to_cart(7, ("Латте", 240))
    first.close()
    second = cafe.Storage(path)  # перезапуск бота
    assert await second.cart(7) == [("Латте", 240)]
    second.close()
