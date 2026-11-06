/* Цены и сроки услуг. Одна таблица на всё портфолио: по ней считает калькулятор на главной,
 * карточки работ показывают цену «такого же», а кнопка «Хочу такой сайт» в демо ведёт
 * в калькулятор с уже выбранными пунктами. Меняете цену здесь — она меняется везде. */
(function () {
  // check — средний чек, от него калькулятор считает цену одного потерянного заказа в день
  const types = [
    { id: "landing", name: "Лендинг", desc: "1 страница", price: 15000, days: 5, typical: "обычно 15–21 тыс.", check: 1500, lost: "одна заявка" },
    { id: "site", name: "Сайт заведения", desc: "до 5 страниц", price: 30000, days: 10, typical: "обычно 37–42 тыс.", check: 1500, lost: "один заказ" },
    { id: "shop", name: "Магазин / каталог", desc: "корзина, фильтры", price: 45000, days: 14, typical: "обычно 45–57 тыс.", check: 3000, lost: "один заказ" },
    { id: "bot", name: "Telegram-бот", desc: "меню и заказы", price: 10000, days: 4, typical: "обычно 10–15 тыс.", check: 1000, lost: "один заказ" },
    { id: "botpro", name: "Бот с записью", desc: "напоминания, оплата", price: 20000, days: 8, typical: "обычно 20–27 тыс.", check: 1500, lost: "одна запись" },
    { id: "miniapp", name: "Telegram Mini App", desc: "приложение в Telegram", price: 40000, days: 14, typical: "обычно 40–52 тыс.", check: 1200, lost: "один заказ" },
  ];
  const opts = [
    { id: "booking", name: "Онлайн-запись или бронь", price: 7000, days: 2 },
    { id: "calc", name: "Калькулятор или квиз", price: 6000, days: 2 },
    { id: "tg", name: "Заявки в Telegram", price: 0, days: 0 },
    { id: "bot", name: "Telegram-бот к сайту", price: 10000, days: 3 },
    { id: "admin", name: "Админка: цены, меню и фото меняете сами", price: 12000, days: 3 },
    { id: "texts", name: "Тексты и подбор фото", price: 5000, days: 1 },
  ];
  // Пилотная цена за отзыв: скидка, предоплата и сколько всего таких мест
  const pilot = { discount: 0.25, prepay: 0.3, total: 5 };
  const BOT_TYPES = ["bot", "botpro", "miniapp"];

  // Из чего состоит каждая работа портфолио, если заказать такую же
  const projects = {
    restaurant: { type: "site", opts: ["booking", "tg"] },
    sushi: { type: "shop", opts: ["admin", "tg"] },
    dental: { type: "site", opts: ["calc", "tg"] },
    autoservice: { type: "site", opts: ["calc", "tg"] },
    miniapp: { type: "miniapp", opts: ["tg"] },
    bar: { type: "site", opts: ["booking", "tg"] },
    florist: { type: "shop", opts: ["tg"] },
    cafe: { type: "site", opts: ["booking", "tg"] },
    gastrobar: { type: "site", opts: ["booking", "tg"] },
    barbershop: { type: "site", opts: ["booking", "tg"] },
    fitness: { type: "site", opts: ["booking", "tg"] },
    realty: { type: "shop", opts: ["calc", "tg"] },
    saas: { type: "landing", opts: ["calc", "tg"] },
    "cafe-bot": { type: "bot", opts: ["tg"] },
  };

  const plural = (n, one, few, many) => {
    const a = n % 10, b = n % 100;
    return a === 1 && b !== 11 ? one : a >= 2 && a <= 4 && (b < 10 || b > 20) ? few : many;
  };
  const rub = (n) => `${n.toLocaleString("ru-RU")} ₽`;

  // Расчёт: полная цена, цена со скидкой, предоплата и срок
  function quote({ type, opts: chosen = [], k = 1, pilot: usePilot = false }) {
    const t = types.find((x) => x.id === type) || types[1];
    // К боту или Mini App ещё один бот не добавляем
    const list = opts.filter((o) => chosen.includes(o.id) && !(BOT_TYPES.includes(t.id) && o.id === "bot"));
    const base = t.price + list.reduce((s, o) => s + o.price, 0);
    const full = Math.round((base * k) / 1000) * 1000;
    const sum = usePilot ? Math.round((full * (1 - pilot.discount)) / 500) * 500 : full;
    const days = Math.max(3, Math.ceil((t.days + list.reduce((s, o) => s + o.days, 0)) / (k > 1 ? 1.5 : 1)));
    return { type: t, opts: list, full, sum, days, prepay: Math.round((sum * pilot.prepay) / 100) * 100 };
  }

  // Ссылка в калькулятор главной с выбранными пунктами
  const calcLink = (slug, root = "../../") => {
    const p = projects[slug];
    return p ? `${root}?type=${p.type}&opts=${p.opts.join(",")}#calc` : `${root}#calc`;
  };

  window.PF_OFFERS = { types, opts, pilot, projects, quote, calcLink, rub, plural, BOT_TYPES };
})();
