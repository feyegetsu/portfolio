"""Реестр сайтов. Один API обслуживает все проекты, у каждого свой набор возможностей."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Site:
    slug: str
    name: str
    leads: bool = False      # заявки: бронь, консультация, просмотр, подписка
    bookings: bool = False   # запись на время
    exclusive_slots: bool = False  # слот может занять только один человек (мастер, а не групповое занятие)
    orders: bool = False     # заказы с корзиной
    catalog: bool = False    # каталог, которым управляют из админки


SITES: dict[str, Site] = {
    s.slug: s
    for s in [
        Site("cafe", "Кофейня «Зерно»", leads=True),
        Site("florist", "Пион & Ко", leads=True, orders=True),
        Site("barbershop", "Барбершоп BLADE", bookings=True, exclusive_slots=True),
        Site("dental", "Стоматология «Белая линия»", leads=True),
        Site("fitness", "Фитнес-клуб PULSE", leads=True, bookings=True),
        Site("autoservice", "Автосервис «МоторЛайн»", leads=True),
        Site("realty", "Агентство «Квадрат»", leads=True),
        Site("saas", "Taskly", leads=True),
        Site("miniapp", "Сытый Лис", orders=True, catalog=True),
    ]
}
