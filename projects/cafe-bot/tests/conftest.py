"""Тесты бота: обработчики вызываются напрямую, Telegram заменён заглушками, база — временный файл."""

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("BOT_TOKEN", "123:test")
os.environ.setdefault("ADMIN_ID", "42")

ADMIN = 42


@pytest.fixture(autouse=True)
def tmp_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def user(uid=7, name="Анна"):
    return SimpleNamespace(id=uid, full_name=name, first_name=name, username=None)


def callback(data, uid=7, text=""):
    """Нажатие инлайн-кнопки: data — callback_data, message — сообщение с кнопками."""
    message = SimpleNamespace(text=text, edit_text=AsyncMock(), edit_reply_markup=AsyncMock(), answer=AsyncMock())
    return SimpleNamespace(data=data, from_user=user(uid), message=message, answer=AsyncMock())


def message(text, uid=7):
    return SimpleNamespace(text=text, from_user=user(uid), answer=AsyncMock())


@pytest.fixture
def bot():
    return SimpleNamespace(send_message=AsyncMock())
