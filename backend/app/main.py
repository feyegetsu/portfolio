"""Точка входа: uvicorn app.main:app (схему базы перед этим обновляет python -m app.migrate)"""

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, check_secrets, settings
from .db import SessionLocal, engine
from .deps import RedisStore, rate_limit, read_limit
from .migrate import is_up_to_date
from .routers import admin, auth, public
from .seed import seed
from .sites import SITES


TOO_LARGE = "Слишком большой запрос"


@asynccontextmanager
async def lifespan(_: FastAPI):
    check_secrets(settings)
    # Схему создают и обновляют миграции (python -m app.migrate), API только проверяет, что она актуальна
    if not is_up_to_date(engine):
        raise RuntimeError("Схема базы устарела или не создана: выполните python -m app.migrate")
    with SessionLocal() as db:
        seed(db)
    yield


class BodyLimit:
    """Отклоняет слишком большие запросы до разбора JSON: формы и заказы весят единицы килобайт.

    Content-Length проверяется сразу, но у chunked-запроса его нет, поэтому байты считаются и по ходу чтения.
    HTTPException, а не любое исключение: иначе FastAPI превратит его в 400 «ошибка разбора тела».
    """

    def __init__(self, app, limit: int) -> None:
        self.app, self.limit = app, limit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        length = dict(scope["headers"]).get(b"content-length", b"")
        if length.isdigit() and int(length) > self.limit:
            return await JSONResponse({"detail": TOO_LARGE}, status_code=413)(scope, receive, send)
        seen = 0

        async def limited():
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > self.limit:
                    raise StarletteHTTPException(413, TOO_LARGE)
            return message

        await self.app(scope, limited, send)


service = APIRouter(tags=["service"])


@service.get("/health")
def health():
    """Для хостинга: жива ли база и где считаются лимиты. Если база недоступна — 503, и хостинг перезапустит API."""
    try:
        with SessionLocal() as db:
            db.execute(text("select 1"))
    except Exception:  # noqa: BLE001 — любой сбой базы означает «не готов»
        return JSONResponse({"status": "error", "db": "unavailable"}, status_code=503)
    return {"status": "ok", "db": "ok", "limits": "redis" if isinstance(rate_limit.store, RedisStore) else "memory"}


@service.get("/api/v1/sites", dependencies=[Depends(read_limit)])
def sites():
    return [{"slug": s.slug, "name": s.name, "leads": s.leads, "bookings": s.bookings, "orders": s.orders, "catalog": s.catalog}
            for s in SITES.values()]


def create_app(s: Settings = settings) -> FastAPI:
    # Документация открыта только в разработке: в продакшене карта админских эндпоинтов не нужна посторонним
    docs = s.env == "development"
    app = FastAPI(
        title="Portfolio API",
        version="1.0.0",
        description="Общий бэкенд для демо-сайтов портфолио: заявки, записи, заказы, каталог и админка.",
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_middleware(BodyLimit, limit=s.max_body_bytes)
    for router in (public.router, auth.router, admin.router, service):
        app.include_router(router)
    return app


app = create_app()
