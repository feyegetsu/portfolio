"""Реестр сайтов. Один API обслуживает все проекты, у каждого свой набор возможностей и свои правила."""

from dataclasses import dataclass, field
from datetime import datetime

Hours = tuple[int, int]  # первый час и «после последнего»; (19, 2) — окно переходит за полночь


@dataclass(frozen=True)
class Pricing:
    """Как сервер считает заказ. Клиент присылает только позиции и количество, цены здесь и в каталоге."""

    delivery: int = 0             # стоимость доставки
    free_from: int = 0            # бесплатная доставка от суммы (после скидки)
    sizes: tuple[tuple[str, int], ...] = ()   # размеры: подпись и доплата к базовой цене
    extras: tuple[tuple[str, int], ...] = ()  # добавки: подпись и цена
    sized_categories: frozenset[str] = frozenset()  # у каких разделов каталога есть размеры и добавки
    promos: dict[str, int] = field(default_factory=dict)  # промокод → скидка в процентах


# Все заведения портфолио в Москве; отчёты по нескольким сайтам (статистика) считаются в этом поясе
DEFAULT_TZ = "Europe/Moscow"


@dataclass(frozen=True)
class Site:
    slug: str
    name: str
    leads: bool = False      # заявки: бронь, консультация, просмотр, подписка
    bookings: bool = False   # запись на время
    exclusive_slots: bool = False  # слот может занять только один человек (мастер, а не групповое занятие)
    orders: bool = False     # заказы с корзиной
    catalog: bool = False    # каталог, которым управляют из админки
    pricing: Pricing | None = None
    # Правила записи: время заведения, сетка слотов, часы работы и насколько вперёд можно записаться
    tz: str = DEFAULT_TZ
    step_minutes: int = 30
    hours: Hours = (10, 22)  # окно записи: первый и «после последнего» час; (19, 2) — после полуночи
    # Окно записи по дням недели (0 — понедельник). Дня нет в словаре — выходной. Ночные часы относятся
    # к дню открытия: запись на 01:00 четверга — это вечер среды. None — каждый день по hours
    schedule: dict[int, Hours] | None = None
    horizon_days: int = 60
    # Кого или что можно забронировать и сколько мест; None у ресурса — эксклюзивный слот
    resources: dict[str, int | None] | None = None
    slot_capacity: int | None = None  # сколько броней на одно время по всему заведению

    def is_open(self, minutes: int) -> bool:
        return _evening(self.hours, minutes) or _night(self.hours, minutes)

    def opening_day(self, dt: datetime) -> int | None:
        """День недели, к которому относится время по расписанию (вечер или ночь после него); None — закрыто."""
        m, wd = dt.hour * 60 + dt.minute, dt.weekday()
        schedule = self.schedule if self.schedule is not None else dict.fromkeys(range(7), self.hours)
        if wd in schedule and _evening(schedule[wd], m):
            return wd
        prev = (wd - 1) % 7
        if prev in schedule and _night(schedule[prev], m):
            return prev
        return None

    def closed_all_day(self, dt: datetime) -> bool:
        """В этот календарный день заведение не открывается (выходной), а не просто «не те часы»."""
        return self.schedule is not None and dt.weekday() not in self.schedule


def _evening(hours: Hours, m: int) -> bool:
    start, end = hours[0] * 60, hours[1] * 60
    return start <= m < end if start < end else m >= start


def _night(hours: Hours, m: int) -> bool:
    start, end = hours[0] * 60, hours[1] * 60
    return start >= end and m < end


MINIAPP_PRICING = Pricing(
    delivery=199, free_from=1500,
    sizes=(("25 см", -120), ("30 см", 0), ("35 см", 170)),
    extras=(("Двойной сыр", 90), ("Халапеньо", 50), ("Бортик с сыром", 120)),
    sized_categories=frozenset({"Пицца"}),
    promos={"FOX10": 10},
)

FITNESS_CLASSES = {
    "Утренняя йога": 14, "Функциональный тренинг": 16, "Пилатес": 12, "Сайкл": 20, "Бокс для начинающих": 12,
    "Кроссфит": 15, "Zumba": 25, "Тайский бокс": 10, "Стретчинг": 18, "Pump": 16,
}

SITES: dict[str, Site] = {
    s.slug: s
    for s in [
        Site("cafe", "Кофейня «Зерно»", leads=True),
        Site("florist", "Пион & Ко", leads=True, orders=True, catalog=True, pricing=Pricing(delivery=390, free_from=5000)),
        Site("barbershop", "Барбершоп BLADE", bookings=True, exclusive_slots=True, step_minutes=60, hours=(10, 21),
             horizon_days=30, resources={"Артём": None, "Денис": None, "Игорь": None}),
        Site("dental", "Стоматология «Белая линия»", leads=True),
        Site("fitness", "Фитнес-клуб PULSE", leads=True, bookings=True, hours=(7, 22), horizon_days=14, resources=FITNESS_CLASSES),
        Site("autoservice", "Автосервис «МоторЛайн»", leads=True),
        Site("realty", "Агентство «Квадрат»", leads=True),
        Site("saas", "Taskly", leads=True),
        Site("miniapp", "Сытый Лис", orders=True, catalog=True, pricing=MINIAPP_PRICING),
        # Вт–Вс с 18:00 до 00:00, последняя бронь в 22:30; понедельник — выходной
        Site("restaurant", "Ресторан «Терруар»", leads=True, bookings=True, hours=(18, 23), horizon_days=30, slot_capacity=10,
             schedule=dict.fromkeys(range(1, 7), (18, 23))),
        Site("sushi", "Суши «Кайсэн»", orders=True, catalog=True, pricing=Pricing(delivery=199, free_from=1500)),
        # Пн–Чт 12:00–00:00, Пт–Вс 12:00–02:00
        Site("gastrobar", "Гастробар «Соль и Солод»", leads=True, bookings=True, hours=(12, 2), slot_capacity=20,
             schedule={**dict.fromkeys(range(4), (12, 24)), **dict.fromkeys(range(4, 7), (12, 2))}),
        # Ср–Вс с 19:00 до 03:00, бронь до 01:30
        Site("bar", "Бар «Полночь»", leads=True, bookings=True, hours=(19, 2), horizon_days=30, slot_capacity=8,
             schedule=dict.fromkeys(range(2, 7), (19, 2))),
    ]
}
