"""Точка входа: uvicorn app.main:app"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, SessionLocal, engine
from .routers import admin, auth, public
from .seed import seed
from .sites import SITES


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Для портфолио таблицы создаются при старте; в продакшене это работа миграций (Alembic)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(
    title="Portfolio API",
    version="1.0.0",
    description="Общий бэкенд для демо-сайтов портфолио: заявки, записи, заказы, каталог и админка.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(public.router)
app.include_router(auth.router)
app.include_router(admin.router)


@app.get("/health", tags=["service"])
def health():
    return {"status": "ok"}


@app.get("/api/v1/sites", tags=["service"])
def sites():
    return [{"slug": s.slug, "name": s.name, "leads": s.leads, "bookings": s.bookings, "orders": s.orders, "catalog": s.catalog}
            for s in SITES.values()]
