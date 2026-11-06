"""Расчёт заказа на сервере: цена из каталога, размеры и добавки по таблице, промокод и доставка.

Браузер присылает только ref и количество. Цена из запроса не используется, поэтому подменить её нельзя.
ref «1» — позиция каталога, «1:2:0-1» — та же позиция с размером №2 и добавками №0 и №1.
"""

from fastapi import HTTPException, status

from .models import CatalogItem
from .schemas import OrderItem
from .sites import Pricing

SERVICE_REFS = {"delivery", "promo"}  # строки, которые раньше присылал браузер: теперь их считает сервер


def _bad(msg: str) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, msg)


def _line(item: OrderItem, catalog: dict[str, CatalogItem], rules: Pricing) -> dict:
    parts = item.ref.split(":")
    base = catalog.get(parts[0])
    if not base:
        raise _bad(f"Позиции «{item.name}» нет в меню, обновите страницу")
    if not base.active:
        raise HTTPException(status.HTTP_409_CONFLICT, f"«{base.name}» закончилось")
    price, mods = base.price, []
    if len(parts) > 1:
        if len(parts) > 3 or base.category not in rules.sized_categories:
            raise _bad(f"У «{base.name}» нет размеров и добавок")
        size, extras = parts[1], parts[2] if len(parts) == 3 else ""
        if size:
            if not size.isdigit() or int(size) >= len(rules.sizes):
                raise _bad(f"Некорректный размер для «{base.name}»")
            label, delta = rules.sizes[int(size)]
            price += delta
            if delta:
                mods.append(label)
        if extras:
            chosen = extras.split("-")
            if len(set(chosen)) != len(chosen) or not all(e.isdigit() and int(e) < len(rules.extras) for e in chosen):
                raise _bad(f"Некорректные добавки для «{base.name}»")
            for e in chosen:
                label, extra_price = rules.extras[int(e)]
                price += extra_price
                mods.append(label.lower())
    name = base.name + (f" ({', '.join(mods)})" if mods else "")
    return {"ref": item.ref, "name": name, "qty": item.qty, "price": price}


def price_order(items: list[OrderItem], catalog: dict[str, CatalogItem], rules: Pricing, mode: str, promo: str) -> list[dict]:
    lines = [_line(i, catalog, rules) for i in items if i.ref not in SERVICE_REFS]
    if not lines:
        raise _bad("Корзина пуста")
    subtotal = sum(line["price"] * line["qty"] for line in lines)
    discount = 0
    code = promo.strip().upper()
    if code:
        percent = rules.promos.get(code)
        if not percent:
            raise _bad("Такого промокода нет")
        discount = int(subtotal * percent / 100 + 0.5)  # округление как Math.round в браузере
        lines.append({"ref": "promo", "name": f"Промокод {code} (−{percent}%)", "qty": 1, "price": -discount})
    if mode == "delivery" and rules.delivery and subtotal - discount < rules.free_from:
        lines.append({"ref": "delivery", "name": "Доставка", "qty": 1, "price": rules.delivery})
    return lines
