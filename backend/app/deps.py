"""Общие зависимости роутов: сессия БД, сайт из пути и IP посетителя.

Авторизация — app/auth.py, лимиты частоты — app/limits.py, правила записи — app/services/booking.py.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .config import Settings, settings
from .db import get_db
from .sites import SITES, Site

DB = Annotated[Session, Depends(get_db)]


def get_site(site: str) -> Site:
    if site not in SITES:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сайт не найден")
    return SITES[site]


def client_ip(request: Request, s: "Settings | None" = None) -> str:
    """IP посетителя для лимитов.

    Первому элементу X-Forwarded-For верить нельзя: его задаёт клиент. Каждый доверенный прокси дописывает
    адрес того, кто к нему пришёл, в конец цепочки, поэтому реальный адрес — TRUSTED_PROXY_HOPS-й справа.
    Если цепочка короче, заголовок подделан или прокси настроен иначе: берём адрес соединения.
    """
    hops = (s or settings).trusted_proxy_hops
    if hops > 0:
        chain = [h.strip() for h in request.headers.get("x-forwarded-for", "").split(",") if h.strip()]
        if len(chain) >= hops:
            return chain[-hops]
    return request.client.host if request.client else "unknown"
