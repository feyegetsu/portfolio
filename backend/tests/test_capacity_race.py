"""BUG-001: вместимость не превышается и при одновременных бронированиях."""

import threading
from collections import Counter
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app import migrate
from app.db import make_engine
from app.models import Booking, SlotCounter
from app.services.booking import release, reserve, site_now
from app.sites import SITES

RESTAURANT = SITES["restaurant"]


@pytest.fixture
def sessions(tmp_path):
    # Файловая база и отдельные соединения: как у нескольких воркеров API
    engine = make_engine(f"sqlite:///{(tmp_path / 'race.db').as_posix()}")
    migrate.upgrade(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)
    engine.dispose()


def slot(days: int = 1) -> datetime:
    return (site_now(RESTAURANT) + timedelta(days=days)).replace(hour=20, minute=0, second=0, microsecond=0)


def book(Session, starts_at: datetime, name: str) -> int:
    with Session() as db:
        try:
            reserve(db, RESTAURANT, "Стол на 2", starts_at)
        except HTTPException as e:
            return e.status_code
        db.add(Booking(site="restaurant", resource="Стол на 2", starts_at=starts_at, name=name, phone="+79001234567"))
        db.commit()
        return 201


def test_last_seat_goes_to_one_of_two_sessions(sessions):
    when = slot()
    for i in range(RESTAURANT.slot_capacity - 1):
        assert book(sessions, when, f"g{i}") == 201
    first = sessions()
    reserve(first, RESTAURANT, "Стол на 2", when)  # последнее место занято, транзакция ещё открыта
    result = {}
    second = threading.Thread(target=lambda: result.update(code=book(sessions, when, "second")))
    second.start()
    second.join(0.5)  # вторая сессия ждёт: база не даёт ей прочитать «осталось одно место» до коммита первой
    first.add(Booking(site="restaurant", resource="Стол на 2", starts_at=when, name="first", phone="+79001234567"))
    first.commit()
    first.close()
    second.join()
    assert result["code"] == 409


def test_concurrent_bookings_never_exceed_capacity(sessions):
    when, n = slot(2), 40
    barrier = threading.Barrier(n)
    codes, lock = [], threading.Lock()

    def worker(i):
        barrier.wait()
        code = book(sessions, when, f"g{i}")
        with lock:
            codes.append(code)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert Counter(codes) == {201: RESTAURANT.slot_capacity, 409: n - RESTAURANT.slot_capacity}
    with sessions() as db:
        assert db.scalar(select(func.count()).select_from(Booking)) == RESTAURANT.slot_capacity
        assert db.scalar(select(SlotCounter.taken)) == RESTAURANT.slot_capacity


def test_release_frees_a_seat(sessions):
    when = slot(3)
    for i in range(RESTAURANT.slot_capacity):
        assert book(sessions, when, f"g{i}") == 201
    assert book(sessions, when, "extra") == 409
    with sessions() as db:
        release(db, RESTAURANT, "Стол на 2", when)
        db.commit()
    assert book(sessions, when, "extra") == 201
