"""Реестр сайтов. Один API обслуживает все проекты, у каждого свой набор возможностей и свои правила."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Pricing:
    """Как сервер считает заказ. Клиент присылает только позиции и количество, цены здесь и в каталоге."""

    delivery: int = 0             # стоимость доставки
    free_from: int = 0            # бесплатная доставка от суммы (после скидки)
    sizes: tuple[tuple[str, int], ...] = ()   # размеры: подпись и доплата к базовой цене
    extras: tuple[tuple[str, int], ...] = ()  # добавки: подпись и цена
    sized_categories: frozenset[str] = frozenset()  # у каких разделов каталога есть размеры и добавки
    promos: dict[str, int] = field(default_factory=dict)  # промокод → скидка в процентах


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
    tz: str = "Europe/Moscow"
    step_minutes: int = 30
    hours: tuple[int, int] = (10, 22)  # первый и «после последнего» час; (19, 2) — работает после полуночи
    horizon_days: int = 60
    # Кого или что можно забронировать и сколько мест; None у ресурса — эксклюзивный слот
    resources: dict[str, int | None] | None = None
    slot_capacity: int | None = None  # сколько броней на одно время по всему заведению

    def is_open(self, minutes: int) -> bool:
        start, end = self.hours[0] * 60, self.hours[1] * 60
        return start <= minutes < end if start < end else minutes >= start or minutes < end


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
        Site("restaurant", "Ресторан «Терруар»", leads=True, bookings=True, hours=(18, 23), horizon_days=30, slot_capacity=10),
        Site("sushi", "Суши «Кайсэн»", orders=True, catalog=True, pricing=Pricing(delivery=199, free_from=1500)),
        Site("gastrobar", "Гастробар «Соль и Солод»", leads=True, bookings=True, hours=(12, 24), slot_capacity=20),
        Site("bar", "Бар «Полночь»", leads=True, bookings=True, hours=(19, 2), horizon_days=30, slot_capacity=8),
    ]
}
