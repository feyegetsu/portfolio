"""SEC-006: собранный сайт с Content-Security-Policy работает без нарушений политики на всех страницах."""

import functools
import json
import subprocess
import sys
import threading
from http.server import ThreadingHTTPServer

import pytest
from conftest import ROOT, QuietHandler

DEMOS = [d["slug"] for d in json.loads((ROOT / "projects" / "demos.json").read_text(encoding="utf-8"))["demos"]]
PAGES = ["", "privacy.html", "404.html", "admin/", *(f"projects/{s}/" for s in DEMOS)]


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("site") / "_site"
    subprocess.run([sys.executable, str(ROOT / "tools" / "build.py"), str(out), "--no-prerender", "--no-minify"],
                   check=True, capture_output=True)
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(QuietHandler, directory=str(out)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield out, f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_every_page_has_csp(built):
    out, _ = built
    pages = list(out.rglob("*.html"))
    assert pages
    missing = [str(p.relative_to(out)) for p in pages if 'http-equiv="Content-Security-Policy"' not in p.read_text(encoding="utf-8")]
    assert not missing


@pytest.mark.parametrize("path", PAGES)
def test_no_csp_violations(built, page, path):
    _, base = built
    page.add_init_script("""window.__csp = [];
      document.addEventListener('securitypolicyviolation', (e) => window.__csp.push(`${e.violatedDirective} ${e.blockedURI}`));""")
    page.goto(f"{base}/{path}", wait_until="networkidle")
    page.wait_for_timeout(300)
    assert page.evaluate("() => window.__csp") == []
