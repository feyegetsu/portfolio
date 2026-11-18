"""Сквозные тесты сайта в настоящем браузере (Playwright).

    pip install -r tests-e2e/requirements.txt && python -m playwright install chromium
    pytest tests-e2e

Фикстура site поднимает статический сервер с корнем репозитория, api — настоящий FastAPI на SQLite
(для сценариев в режиме ?api=). У каждого теста свой контекст браузера: свой localStorage, демо с нуля.
"""

import functools
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
OWNER = ("owner@e2e.dev", "e2e-owner-password")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass

    def end_headers(self) -> None:
        # Без кеша: каждый тест видит текущие файлы
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def site():
    """Адрес сайта: http://127.0.0.1:<порт> без завершающего слеша."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture(scope="session")
def api(site, tmp_path_factory):
    """Настоящий API на SQLite: адрес и заголовок владельца для проверок через HTTP."""
    port = free_port()
    db = tmp_path_factory.mktemp("api") / "e2e.db"
    env = {**os.environ, "ENV": "development", "DATABASE_URL": f"sqlite:///{db.as_posix()}", "CORS_ORIGINS": site,
           "OWNER_EMAIL": OWNER[0], "OWNER_PASSWORD": OWNER[1], "RATE_LIMIT": "1000", "PYTHONUTF8": "1"}
    subprocess.run([sys.executable, "-m", "app.migrate"], cwd=BACKEND, env=env, check=True, capture_output=True)
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(port)],
                            cwd=BACKEND, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            urllib.request.urlopen(f"{base}/health", timeout=1)
            break
        except OSError:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("API не запустился")
    yield base
    proc.terminate()
    proc.wait(10)


@pytest.fixture
def browser_context_args(browser_context_args):
    # Демо рассчитаны на Москву; webdriver-флаг Playwright уже выставляет сам
    return {**browser_context_args, "locale": "ru-RU", "timezone_id": "Europe/Moscow", "viewport": {"width": 1280, "height": 900}}


@pytest.fixture
def errors(page):
    """Ошибки JavaScript на странице: тест падает, если они были."""
    found: list[str] = []
    page.on("pageerror", lambda e: found.append(str(e)))
    yield found
    assert not found, f"Ошибки JavaScript: {found}"


def demo_login(page, site: str) -> None:
    """Вход владельцем в демо-админку на уже открытой странице того же сайта (общий localStorage)."""
    page.evaluate("() => PortfolioAPI.login('demo@feyegetsu.dev', 'demo')")
