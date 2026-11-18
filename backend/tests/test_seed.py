"""BUG-003: начальный каталог заливается один раз, удалённые позиции не возвращаются после перезапуска."""

from sqlalchemy import delete, func, select

from app.db import SessionLocal
from app.models import CatalogItem
from app.seed import CATALOGS, seed


def count(db, site):
    return db.scalar(select(func.count()).select_from(CatalogItem).where(CatalogItem.site == site))


def test_deleted_catalog_is_not_reseeded(client):
    with SessionLocal() as db:
        assert count(db, "florist") == len(CATALOGS["florist"])
        db.execute(delete(CatalogItem).where(CatalogItem.site == "florist"))
        db.commit()
        seed(db)  # перезапуск API
        assert count(db, "florist") == 0


def test_seed_is_idempotent(client):
    with SessionLocal() as db:
        seed(db)
        seed(db)
        assert count(db, "sushi") == len(CATALOGS["sushi"])
