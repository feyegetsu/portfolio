/*
 * Клиент API для демо-сайтов и админки.
 *
 * Два режима с одинаковым интерфейсом:
 *  - remote: запросы к бэкенду из /backend (FastAPI). Включается параметром ?api=https://адрес-api
 *            (запоминается в браузере, ?api=off возвращает демо) или переменной window.PORTFOLIO_API;
 *  - demo:   тот же контракт и те же правила (валидация, занятые слоты, цены из каталога, роли),
 *            но данные хранятся в localStorage. Так всё работает на GitHub Pages без сервера,
 *            а заявка с сайта появляется в админке, открытой в соседней вкладке, без перезагрузки.
 */
(() => {
  // Адрес этого файла: рядом лежит offers.js с ценами для кнопки «Хочу такой сайт»
  const SCRIPT_SRC = document.currentScript && document.currentScript.src;
  // Те же правила, что в backend/app/sites.py: демо-режим ведёт себя как настоящий сервер
  const FITNESS_CLASSES = { "Утренняя йога": 14, "Функциональный тренинг": 16, "Пилатес": 12, "Сайкл": 20, "Бокс для начинающих": 12, "Кроссфит": 15, "Zumba": 25, "Тайский бокс": 10, "Стретчинг": 18, "Pump": 16 };
  const MINIAPP_PRICING = {
    delivery: 199, freeFrom: 1500, sized: ["Пицца"], promos: { FOX10: 10 },
    sizes: [["25 см", -120], ["30 см", 0], ["35 см", 170]],
    extras: [["Двойной сыр", 90], ["Халапеньо", 50], ["Бортик с сыром", 120]],
  };
  const SITES = [
    { slug: "cafe", name: "Кофейня «Зерно»", leads: true },
    { slug: "florist", name: "Пион & Ко", leads: true, orders: true, catalog: true, pricing: { delivery: 390, freeFrom: 5000 } },
    { slug: "barbershop", name: "Барбершоп BLADE", bookings: true, exclusive: true, step: 60, hours: [10, 21], horizon: 30, resources: { "Артём": null, "Денис": null, "Игорь": null } },
    { slug: "dental", name: "Стоматология «Белая линия»", leads: true },
    { slug: "fitness", name: "Фитнес-клуб PULSE", leads: true, bookings: true, hours: [7, 22], horizon: 14, resources: FITNESS_CLASSES },
    { slug: "autoservice", name: "Автосервис «МоторЛайн»", leads: true },
    { slug: "realty", name: "Агентство «Квадрат»", leads: true },
    { slug: "saas", name: "Taskly", leads: true },
    { slug: "miniapp", name: "Сытый Лис", orders: true, catalog: true, pricing: MINIAPP_PRICING },
    { slug: "restaurant", name: "Ресторан «Терруар»", leads: true, bookings: true, hours: [18, 23], horizon: 30, capacity: 10 },
    { slug: "sushi", name: "Суши «Кайсэн»", orders: true, catalog: true, pricing: { delivery: 199, freeFrom: 1500 } },
    { slug: "gastrobar", name: "Гастробар «Соль и Солод»", leads: true, bookings: true, hours: [12, 24], capacity: 20 },
    { slug: "bar", name: "Бар «Полночь»", leads: true, bookings: true, hours: [19, 2], horizon: 30, capacity: 8 },
  ];
  // Каталоги, которыми управляют из админки; ref совпадает с id позиции на сайте
  const SUSHI_MENU = [["s1", "Сет «Кайсэн»", "Сеты", 2490], ["s2", "Сет «Филадельфия»", "Сеты", 1890], ["s3", "Сет для двоих", "Сеты", 1390], ["s4", "Филадельфия", "Роллы", 590], ["s5", "Калифорния", "Роллы", 490], ["s6", "Радуга", "Роллы", 650], ["s7", "Маки с огурцом", "Роллы", 190], ["s8", "Красный дракон", "Роллы", 690], ["s9", "Запечённый с лососем", "Запечённые", 560], ["s10", "Запечённый с крабом", "Запечённые", 520], ["s11", "Нигири с лососем", "Нигири и сашими", 220], ["s12", "Сашими-ассорти", "Нигири и сашими", 990], ["s13", "Нигири микс", "Нигири и сашими", 690], ["s14", "Рамен тонкоцу", "Горячее", 590], ["s15", "Острый рамен с курицей", "Горячее", 560], ["s16", "Гёдза со свининой", "Горячее", 390], ["s17", "Якитори", "Горячее", 450]];
  const FLORIST_MENU = [["1", "Утренний сад", "Авторские", 4900], ["2", "Тюльпаны микс", "Монобукеты", 3200], ["3", "Классика", "Розы", 8900], ["4", "Солнечный день", "Авторские", 2700], ["5", "Яркое настроение", "Авторские", 3900], ["6", "Нежность", "Авторские", 5400], ["7", "Ромашки", "Монобукеты", 1900], ["8", "Кактус в кашпо", "Растения", 1500], ["9", "Розовые тюльпаны", "Монобукеты", 2600], ["10", "Лилии", "Монобукеты", 3300], ["11", "Суккулент", "Растения", 1200], ["12", "Пионовидные розы", "Розы", 5900]];
  const LATER_CATALOGS = { sushi: SUSHI_MENU, florist: FLORIST_MENU };
  const SITE = Object.fromEntries(SITES.map((s) => [s.slug, s]));
  const ROLE_LEVEL = { staff: 1, admin: 2, owner: 3 };

  class ApiError extends Error {
    constructor(message, status) {
      super(message);
      this.status = status;
    }
  }

  const normalizePhone = (v) => {
    const cleaned = String(v || "").replace(/[^\d+]/g, "");
    if (!/^\+?\d{10,15}$/.test(cleaned)) throw new ApiError("Некорректный номер телефона", 422);
    return cleaned;
  };
  const normalizeEmail = (v) => {
    const e = String(v || "").trim().toLowerCase();
    if (e && !/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(e)) throw new ApiError("Некорректный e-mail", 422);
    return e;
  };

  // Расчёт заказа как на сервере (backend/app/pricing.py): цена из каталога, размеры, добавки, промокод, доставка
  function priceOrder(rules, catalog, items, mode, promo) {
    const bad = (m) => new ApiError(m, 422);
    const lines = items.filter((i) => !["delivery", "promo"].includes(String(i.ref))).map((i) => {
      const parts = String(i.ref || "").split(":");
      const base = catalog.find((c) => c.ref === parts[0]);
      if (!base) throw bad(`Позиции «${i.name || i.ref}» нет в меню, обновите страницу`);
      if (!base.active) throw new ApiError(`«${base.name}» закончилось`, 409);
      const qty = Number(i.qty);
      if (!Number.isInteger(qty) || qty < 1 || qty > 99) throw bad("Количество от 1 до 99");
      let price = base.price;
      const mods = [];
      if (parts.length > 1) {
        if (parts.length > 3 || !(rules.sized || []).includes(base.category)) throw bad(`У «${base.name}» нет размеров и добавок`);
        const [, size, extras = ""] = parts;
        if (size) {
          if (!/^\d+$/.test(size) || +size >= rules.sizes.length) throw bad(`Некорректный размер для «${base.name}»`);
          price += rules.sizes[+size][1];
          if (rules.sizes[+size][1]) mods.push(rules.sizes[+size][0]);
        }
        if (extras) {
          const chosen = extras.split("-");
          if (new Set(chosen).size !== chosen.length || !chosen.every((e) => /^\d+$/.test(e) && +e < rules.extras.length)) throw bad(`Некорректные добавки для «${base.name}»`);
          for (const e of chosen) { price += rules.extras[+e][1]; mods.push(rules.extras[+e][0].toLowerCase()); }
        }
      }
      return { ref: String(i.ref), name: base.name + (mods.length ? ` (${mods.join(", ")})` : ""), qty, price };
    });
    if (!lines.length) throw bad("Корзина пуста");
    const subtotal = lines.reduce((t, l) => t + l.price * l.qty, 0);
    let discount = 0;
    const code = String(promo || "").trim().toUpperCase();
    if (code) {
      const percent = (rules.promos || {})[code];
      if (!percent) throw bad("Такого промокода нет");
      discount = Math.round((subtotal * percent) / 100);
      lines.push({ ref: "promo", name: `Промокод ${code} (−${percent}%)`, qty: 1, price: -discount });
    }
    if (mode === "delivery" && rules.delivery && subtotal - discount < rules.freeFrom) lines.push({ ref: "delivery", name: "Доставка", qty: 1, price: rules.delivery });
    return lines;
  }

  // Правила записи как на сервере: не в прошлом, не дальше горизонта, по сетке, в часы работы, к существующему ресурсу
  function checkSlot(s, resource, startsAt) {
    const bad = (m) => new ApiError(m, 422);
    const t = new Date(startsAt);
    if (Number.isNaN(+t)) throw bad("Некорректное время");
    if (t < new Date(Date.now() - 5 * 60000)) throw bad("Это время уже прошло");
    if (t > new Date(Date.now() + (s.horizon || 60) * 86400000)) throw bad(`Запись открыта на ${s.horizon || 60} дней вперёд`);
    if (t.getMinutes() % (s.step || 30)) throw bad("Выберите время из расписания");
    const m = t.getHours() * 60 + t.getMinutes();
    const [open, close] = (s.hours || [10, 22]).map((h) => h * 60);
    if (!(open < close ? m >= open && m < close : m >= open || m < close)) throw bad("В это время мы закрыты");
    if (s.resources && !(resource in s.resources)) throw bad("Такого мастера или занятия нет");
  }
  const newToken = () => Array.from(crypto.getRandomValues(new Uint8Array(12)), (b) => b.toString(16).padStart(2, "0")).join("");
  // Текст, похожий на формулу, Excel покажет как текст, а не выполнит
  const csvSafe = (v) => (/^[=+\-@\t\r]/.test(String(v ?? "")) ? "'" + v : String(v ?? ""));

  // ---------- Выбор режима ----------
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch {} },
    del(k) { try { localStorage.removeItem(k); } catch {} },
  };
  // Адрес API: в проекте клиента он зашит в window.PORTFOLIO_API, и параметр ссылки игнорируется.
  // В портфолио ?api= работает, но чужой адрес подключается только после явного подтверждения:
  // иначе ссылка вида …/admin/?api=https://evil.example увела бы логин и пароль на чужой сервер
  const qp = new URLSearchParams(location.search).get("api");
  const isLocal = (u) => { try { return ["localhost", "127.0.0.1", "[::1]"].includes(new URL(u).hostname); } catch { return false; } };
  const validUrl = (u) => { try { return ["http:", "https:"].includes(new URL(u).protocol); } catch { return false; } };
  if (!window.PORTFOLIO_API) {
    if (qp === "off") store.del("pf-api");
    else if (qp && validUrl(qp)) {
      const url = qp.replace(/\/$/, "");
      const ok = isLocal(url) || confirm(`Подключить сайт к серверу ${new URL(url).host}?\n\nЗаявки и пароль от админки будут уходить на этот адрес. Нажимайте «ОК», только если это ваш сервер.`);
      if (ok) store.set("pf-api", url);
    }
  }
  const BASE = window.PORTFOLIO_API || (qp !== "off" && store.get("pf-api")) || "";

  // =====================================================================
  // remote: настоящий бэкенд
  // =====================================================================
  function remoteApi(base) {
    const tokenKey = "pf-token";
    const token = () => { try { return sessionStorage.getItem(tokenKey); } catch { return null; } };

    async function req(method, path, body, { raw } = {}) {
      const headers = { "Content-Type": "application/json" };
      if (token()) headers.Authorization = `Bearer ${token()}`;
      let res;
      try {
        res = await fetch(base + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
      } catch {
        throw new ApiError("Сервер недоступен. Проверьте соединение.", 0);
      }
      if (raw && res.ok) return res;
      const data = res.status === 204 ? null : await res.json().catch(() => null);
      if (!res.ok) {
        const detail = data && data.detail;
        const msg = Array.isArray(detail) ? detail.map((d) => d.msg.replace(/^Value error, /, "")).join("; ") : detail;
        throw new ApiError(msg || `Ошибка ${res.status}`, res.status);
      }
      return data;
    }
    const qs = (o = {}) => {
      const p = Object.entries(o).filter(([, v]) => v !== undefined && v !== null && v !== "");
      return p.length ? "?" + new URLSearchParams(p).toString() : "";
    };

    return {
      mode: "remote",
      base,
      createLead: (site, b) => req("POST", `/api/v1/sites/${site}/leads`, b),
      busySlots: (site, resource, date) => req("GET", `/api/v1/sites/${site}/slots${qs({ resource, date })}`),
      createBooking: (site, b) => req("POST", `/api/v1/sites/${site}/bookings`, b),
      createOrder: (site, b) => req("POST", `/api/v1/sites/${site}/orders`, b),
      orderStatus: (site, id) => req("GET", `/api/v1/sites/${site}/orders/${id}`),
      catalog: (site) => req("GET", `/api/v1/sites/${site}/catalog`),
      async login(email, password) {
        const r = await req("POST", "/api/v1/auth/login", { email, password });
        try { sessionStorage.setItem(tokenKey, r.access_token); } catch {}
        return this.me();
      },
      logout() { try { sessionStorage.removeItem(tokenKey); } catch {} },
      me: () => (token() ? req("GET", "/api/v1/auth/me") : Promise.resolve(null)),
      admin: {
        leads: (f) => req("GET", `/api/v1/admin/leads${qs(f)}`),
        updateLead: (id, status) => req("PATCH", `/api/v1/admin/leads/${id}`, { status }),
        bookings: (f) => req("GET", `/api/v1/admin/bookings${qs(f)}`),
        updateBooking: (id, status) => req("PATCH", `/api/v1/admin/bookings/${id}`, { status }),
        orders: (f) => req("GET", `/api/v1/admin/orders${qs(f)}`),
        updateOrder: (id, status) => req("PATCH", `/api/v1/admin/orders/${id}`, { status }),
        catalog: (f) => req("GET", `/api/v1/admin/catalog${qs(f)}`),
        addCatalog: (site, b) => req("POST", `/api/v1/admin/catalog/${site}`, b),
        updateCatalog: (id, b) => req("PATCH", `/api/v1/admin/catalog/item/${id}`, b),
        deleteCatalog: (id) => req("DELETE", `/api/v1/admin/catalog/item/${id}`),
        stats: (f) => req("GET", `/api/v1/admin/stats${qs(f)}`),
        users: () => req("GET", "/api/v1/admin/users"),
        addUser: (b) => req("POST", "/api/v1/admin/users", b),
        removeUser: (id) => req("DELETE", `/api/v1/admin/users/${id}`),
        exportLeads: async (f) => (await req("GET", `/api/v1/admin/leads.csv${qs(f)}`, null, { raw: true })).text(),
      },
      // Удалённые изменения подтягиваем опросом раз в 15 секунд
      onChange(cb) { const t = setInterval(cb, 15000); return () => clearInterval(t); },
    };
  }

  // =====================================================================
  // demo: тот же контракт поверх localStorage
  // =====================================================================
  function demoApi() {
    const KEY = "pf-db-v1";
    const SESSION = "pf-demo-user";
    const now = () => new Date();
    const iso = (d) => new Date(d).toISOString();
    const pad = (n) => String(n).padStart(2, "0");
    const localIso = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:00`;

    function seedData() {
      const db = { seq: 1, users: [], leads: [], bookings: [], orders: [], catalog: [] };
      const id = () => db.seq++;
      const ago = (days, h = 12, m = 0) => { const d = now(); d.setDate(d.getDate() - days); d.setHours(h, m, 0, 0); return iso(d); };
      db.users.push(
        { id: id(), email: "demo@feyegetsu.dev", password: "demo", name: "Владелец (демо)", role: "owner", sites: null },
        { id: id(), email: "cafe@feyegetsu.dev", password: "demo", name: "Администратор кофейни", role: "staff", sites: ["cafe"] },
      );
      const leads = [
        ["cafe", "table", "Анна Смирнова", "+79161234567", "Столик у окна, будет торт", { date: "", time: "19:00", guests: "4" }, 0, "new"],
        ["dental", "consult", "Игорь Петров", "+79035550101", "Ноет зуб мудрости", { doctor: "Михаил Орлов" }, 0, "new"],
        ["realty", "viewing", "Ольга Ким", "+79260002233", "", { object: "2-комнатная, ЖК «Парк Авеню»" }, 1, "in_progress"],
        ["autoservice", "repair", "Денис Волков", "+79857771122", "Toyota Camry", { works: ["Замена масла", "Диагностика"], total: 2700 }, 1, "new"],
        ["saas", "signup", "", "", "", { email: "team@startup.io" }, 2, "done"],
        ["dental", "quiz", "", "+79031112233", "", { result: "Отбеливание или виниры", range: "24 000 – 120 000 ₽" }, 3, "in_progress"],
        ["cafe", "table", "Михаил Орлов", "+79167778899", "", { time: "12:00", guests: "2" }, 4, "done"],
        ["fitness", "trial", "Екатерина Лис", "+79991234455", "", {}, 5, "done"],
        ["florist", "subscribe", "", "", "", { email: "lena@mail.ru" }, 6, "done"],
        ["realty", "viewing", "Павел Лебедев", "+79095556677", "", { object: "Студия, ул. Садовая, 14" }, 8, "cancelled"],
      ];
      leads.forEach(([site, kind, name, phone, message, data, days, status], i) => {
        db.leads.push({ id: id(), site, kind, name, phone, email: data.email || "", message, data, status, created_at: ago(days, 9 + ((i * 5) % 11), 15) });
      });
      const tomorrow = now(); tomorrow.setDate(tomorrow.getDate() + 1);
      const at = (h) => { const d = new Date(tomorrow); d.setHours(h, 0, 0, 0); return localIso(d); };
      db.bookings.push(
        { id: id(), site: "barbershop", resource: "Артём", service: "Мужская стрижка", starts_at: at(12), name: "Сергей", phone: "+79161112233", status: "confirmed", created_at: ago(0, 9) },
        { id: id(), site: "barbershop", resource: "Денис", service: "Стрижка + борода", starts_at: at(17), name: "Алексей", phone: "+79262223344", status: "confirmed", created_at: ago(1, 18) },
        { id: id(), site: "fitness", resource: "Кроссфит", service: "18:00", starts_at: at(18), name: "Марина", phone: "+79853334455", status: "confirmed", created_at: ago(2, 20) },
      );
      db.orders.push(
        { id: id(), site: "miniapp", items: [{ ref: "1", name: "Маргарита", qty: 2, price: 549 }, { ref: "16", name: "Лимонады", qty: 2, price: 219 }], total: 1536, name: "Никита", phone: "+79031234567", address: "ул. Ленина, 5, кв. 12", mode: "delivery", comment: "", status: "delivering", created_at: ago(0, 13, 40) },
        { id: id(), site: "florist", items: [{ ref: "1", name: "Утренний сад", qty: 1, price: 4900 }], total: 4900, name: "Виктория", phone: "+79165554433", address: "пр. Мира, 7", mode: "delivery", comment: "Позвонить за час", status: "new", created_at: ago(0, 11, 5) },
        { id: id(), site: "miniapp", items: [{ ref: "9", name: "Сет «Лис»", qty: 1, price: 1590 }], total: 1590, name: "Ирина", phone: "+79267778899", address: "", mode: "pickup", comment: "", status: "done", created_at: ago(1, 19, 20) },
        { id: id(), site: "florist", items: [{ ref: "3", name: "Классика", qty: 1, price: 8900 }], total: 8900, name: "Артур", phone: "+79998887766", address: "ул. Цветочная, 22", mode: "delivery", comment: "", status: "done", created_at: ago(3, 15) },
      );
      const menu = [["1", "Маргарита", "Пицца", 549], ["2", "Пепперони", "Пицца", 649], ["3", "Овощная", "Пицца", 599], ["4", "Четыре сезона", "Пицца", 699],
        ["5", "Классик", "Бургеры", 429], ["6", "Пулд-порк", "Бургеры", 469], ["7", "Бургер + фри", "Бургеры", 549], ["8", "Филадельфия", "Роллы", 589],
        ["9", "Сет «Лис»", "Роллы", 1590], ["10", "Нигири микс", "Роллы", 690], ["11", "Боул с курицей", "Боулы", 459], ["12", "Поке с лососем", "Боулы", 549],
        ["13", "Паста с морепродуктами", "Горячее", 589], ["14", "Пенне арабьята", "Горячее", 399], ["15", "Стейк с фри", "Горячее", 890], ["16", "Лимонады", "Напитки", 219]];
      for (const [ref, name, category, price] of menu) db.catalog.push({ id: id(), site: "miniapp", ref, name, category, price, active: true });
      addCatalogs(db);
      return db;
    }

    // Каталоги сайтов, добавленных позже: дописываем в уже сохранённые демо-данные, не трогая остальное
    function addCatalogs(db) {
      let added = false;
      for (const [slug, menu] of Object.entries(LATER_CATALOGS)) {
        if (db.catalog.some((c) => c.site === slug)) continue;
        for (const [ref, name, category, price] of menu) db.catalog.push({ id: db.seq++, site: slug, ref, name, category, price, active: true });
        added = true;
      }
      return added;
    }

    function load() {
      try {
        const raw = store.get(KEY);
        if (raw) {
          const db = JSON.parse(raw);
          if (addCatalogs(db)) save(db);
          return db;
        }
      } catch {}
      const db = seedData();
      save(db);
      return db;
    }
    function save(db) { store.set(KEY, JSON.stringify(db)); }
    // Маленькая задержка, как у сети: интерфейс честно показывает состояние «отправляется»
    const later = (fn) => new Promise((resolve, reject) => setTimeout(() => { try { resolve(fn()); } catch (e) { reject(e); } }, 60));
    const site = (slug, flag) => {
      const s = SITE[slug];
      if (!s) throw new ApiError("Сайт не найден", 404);
      if (flag && !s[flag]) throw new ApiError("Этот сайт так не умеет", 404);
      return s;
    };
    const clone = (o) => JSON.parse(JSON.stringify(o));

    // ---------- сессия и права ----------
    function user() {
      const id = Number(store.get(SESSION));
      return id ? load().users.find((u) => u.id === id) || null : null;
    }
    function requireUser(minRole = "staff") {
      const u = user();
      if (!u) throw new ApiError("Нужно войти", 401);
      if (ROLE_LEVEL[u.role] < ROLE_LEVEL[minRole]) throw new ApiError("Недостаточно прав", 403);
      return u;
    }
    const allowed = (u) => (u.sites === null ? SITES.map((s) => s.slug) : u.sites);
    function scoped(list, u, siteFilter) {
      const sites = allowed(u);
      if (siteFilter && !sites.includes(siteFilter)) throw new ApiError("Нет доступа к этому сайту", 403);
      return list.filter((x) => (siteFilter ? x.site === siteFilter : sites.includes(x.site)));
    }
    const page = (list, { limit = 50, offset = 0 } = {}) => {
      const sorted = [...list].sort((a, b) => (a.created_at < b.created_at ? 1 : -1) || b.id - a.id);
      return { items: clone(sorted.slice(Number(offset), Number(offset) + Number(limit))), total: list.length };
    };
    const publicUser = (u) => ({ id: u.id, email: u.email, name: u.name, role: u.role, sites: u.sites });

    function patch(collection, id, changes, u) {
      const db = load();
      const item = db[collection].find((x) => x.id === Number(id));
      if (!item) throw new ApiError("Не найдено", 404);
      if (!allowed(u).includes(item.site)) throw new ApiError("Нет доступа к этому сайту", 403);
      Object.assign(item, changes);
      save(db);
      return clone(item);
    }

    // Слот занят: у мастера одна запись на время, у занятия и заведения — по числу мест
    function checkTaken(db, s, resource, startsAt, excludeId) {
      const same = db.bookings.filter((x) => x.site === s.slug && x.starts_at === startsAt && x.status !== "cancelled" && x.id !== excludeId
        && (!s.resources || x.resource === resource));
      if (s.exclusive && same.length) throw new ApiError("Это время уже заняли, выберите другое", 409);
      const capacity = s.resources ? s.resources[resource] : s.capacity;
      if (capacity && same.length >= capacity) throw new ApiError("На это время мест уже нет", 409);
    }

    const LEAD_STATUSES = ["new", "in_progress", "done", "cancelled"];
    const BOOKING_STATUSES = ["confirmed", "done", "cancelled"];
    const ORDER_STATUSES = ["new", "cooking", "delivering", "done", "cancelled"];
    const checkStatus = (s, list) => { if (!list.includes(s)) throw new ApiError("Неизвестный статус", 422); };

    return {
      mode: "demo",
      base: "",
      createLead: (slug, b) => later(() => {
        site(slug, "leads");
        const phone = b.phone ? normalizePhone(b.phone) : "";
        const email = normalizeEmail(b.email);
        if (!phone && !email) throw new ApiError("Укажите телефон или e-mail", 422);
        if (JSON.stringify(b.data || {}).length > 4000) throw new ApiError("Слишком много данных в заявке", 422);
        const db = load();
        const lead = { id: db.seq++, site: slug, kind: b.kind, name: b.name || "", phone, email, message: b.message || "", data: b.data || {}, status: "new", created_at: iso(now()) };
        db.leads.push(lead);
        save(db);
        return { id: lead.id, status: lead.status };
      }),
      busySlots: (slug, resource, date) => later(() => {
        site(slug, "bookings");
        return load().bookings
          .filter((b) => b.site === slug && b.resource === resource && b.status !== "cancelled" && b.starts_at.slice(0, 10) === date)
          .map((b) => b.starts_at.slice(11, 16));
      }),
      createBooking: (slug, b) => later(() => {
        const s = site(slug, "bookings");
        const phone = normalizePhone(b.phone);
        if (!b.name) throw new ApiError("Укажите имя", 422);
        const startsAt = String(b.starts_at).slice(0, 16) + ":00";
        checkSlot(s, b.resource, startsAt);
        const db = load();
        checkTaken(db, s, b.resource, startsAt);
        const booking = { id: db.seq++, site: slug, resource: b.resource, service: b.service || "", starts_at: startsAt, name: b.name, phone, status: "confirmed", created_at: iso(now()) };
        db.bookings.push(booking);
        save(db);
        return { id: booking.id, status: booking.status };
      }),
      createOrder: (slug, b) => later(() => {
        const s = site(slug, "orders");
        const phone = normalizePhone(b.phone);
        if (!b.items || !b.items.length) throw new ApiError("Корзина пуста", 422);
        if ((b.mode || "delivery") === "delivery" && !String(b.address || "").trim()) throw new ApiError("Укажите адрес доставки", 422);
        const db = load();
        // Цены, доставку и промокод считаем по каталогу, как сервер: цена из запроса не используется
        const items = priceOrder(s.pricing, db.catalog.filter((c) => c.site === slug), b.items, b.mode || "delivery", b.promo);
        const order = { id: db.seq++, token: newToken(), site: slug, items, total: items.reduce((t, i) => t + i.price * i.qty, 0), name: b.name, phone, address: b.address || "", mode: b.mode || "delivery", comment: b.comment || "", status: "new", created_at: iso(now()) };
        db.orders.push(order);
        save(db);
        return { id: order.id, status: order.status, token: order.token, total: order.total, items: order.items.map(({ name, qty }) => ({ name, qty })) };
      }),
      // Статус по секретному токену из ответа на заказ, а не по порядковому номеру
      orderStatus: (slug, token) => later(() => {
        const o = load().orders.find((x) => x.token && x.token === String(token) && x.site === slug);
        if (!o) throw new ApiError("Заказ не найден", 404);
        return { id: o.id, status: o.status, total: o.total, items: clone(o.items) };
      }),
      catalog: (slug) => later(() => { site(slug, "catalog"); return clone(load().catalog.filter((c) => c.site === slug)); }),

      login: (email, password) => later(() => {
        const u = load().users.find((x) => x.email === String(email).trim().toLowerCase() && x.password === password);
        if (!u) throw new ApiError("Неверный e-mail или пароль", 401);
        store.set(SESSION, String(u.id));
        return publicUser(u);
      }),
      logout() { store.del(SESSION); },
      me: () => later(() => { const u = user(); return u ? publicUser(u) : null; }),

      admin: {
        leads: (f = {}) => later(() => {
          let list = scoped(load().leads, requireUser(), f.site);
          if (f.status) list = list.filter((l) => l.status === f.status);
          if (f.q) {
            const q = f.q.trim().toLowerCase();
            list = list.filter((l) => [l.name, l.phone, l.email, l.message].join(" ").toLowerCase().includes(q));
          }
          return page(list, f);
        }),
        updateLead: (id, status) => later(() => { checkStatus(status, LEAD_STATUSES); return patch("leads", id, { status }, requireUser()); }),
        bookings: (f = {}) => later(() => {
          let list = scoped(load().bookings, requireUser(), f.site);
          if (f.upcoming) list = list.filter((b) => b.status === "confirmed" && new Date(b.starts_at) > new Date(Date.now() - 12 * 3600e3));
          return page(list, f);
        }),
        updateBooking: (id, status) => later(() => {
          checkStatus(status, BOOKING_STATUSES);
          const u = requireUser();
          const b = load().bookings.find((x) => x.id === Number(id));
          // Возврат отменённой записи: слот мог уже занять другой клиент
          if (b && b.status === "cancelled" && status !== "cancelled") checkTaken(load(), SITE[b.site], b.resource, b.starts_at, b.id);
          return patch("bookings", id, { status }, u);
        }),
        orders: (f = {}) => later(() => {
          let list = scoped(load().orders, requireUser(), f.site);
          if (f.status) list = list.filter((o) => o.status === f.status);
          return page(list, f);
        }),
        updateOrder: (id, status) => later(() => { checkStatus(status, ORDER_STATUSES); return patch("orders", id, { status, touched: true }, requireUser()); }),
        catalog: (f = {}) => later(() => clone(scoped(load().catalog, requireUser(), f.site))),
        addCatalog: (slug, b) => later(() => {
          const u = requireUser("admin");
          site(slug, "catalog");
          if (!allowed(u).includes(slug)) throw new ApiError("Нет доступа к этому сайту", 403);
          const db = load();
          if (db.catalog.some((c) => c.site === slug && c.ref === b.ref)) throw new ApiError("Позиция с таким кодом уже есть в каталоге", 409);
          const item = { id: db.seq++, site: slug, ref: b.ref, name: b.name, category: b.category || "", price: Number(b.price), active: b.active !== false };
          db.catalog.push(item);
          save(db);
          return clone(item);
        }),
        updateCatalog: (id, b) => later(() => {
          const changes = {};
          if (b.name !== undefined) changes.name = b.name;
          if (b.price !== undefined) {
            if (!(Number(b.price) >= 0)) throw new ApiError("Цена должна быть числом", 422);
            changes.price = Number(b.price);
          }
          if (b.active !== undefined) changes.active = !!b.active;
          return patch("catalog", id, changes, requireUser("admin"));
        }),
        deleteCatalog: (id) => later(() => {
          const u = requireUser("admin");
          const db = load();
          const item = db.catalog.find((c) => c.id === Number(id));
          if (!item) throw new ApiError("Не найдено", 404);
          if (!allowed(u).includes(item.site)) throw new ApiError("Нет доступа к этому сайту", 403);
          db.catalog = db.catalog.filter((c) => c !== item);
          save(db);
          return null;
        }),
        stats: (f = {}) => later(() => {
          const u = requireUser();
          const db = load();
          const leads = scoped(db.leads, u, f.site), bookings = scoped(db.bookings, u, f.site), orders = scoped(db.orders, u, f.site);
          const days = Number(f.days || 14);
          const byDay = {};
          for (let i = days - 1; i >= 0; i--) { const d = now(); d.setDate(d.getDate() - i); byDay[d.toISOString().slice(0, 10)] = 0; }
          const bySite = {};
          for (const x of [...leads, ...bookings, ...orders]) {
            const k = x.created_at.slice(0, 10);
            if (k in byDay) byDay[k]++;
            bySite[x.site] = (bySite[x.site] || 0) + 1;
          }
          return {
            leads: leads.length, bookings: bookings.length, orders: orders.length,
            revenue: orders.filter((o) => o.status !== "cancelled").reduce((t, o) => t + o.total, 0),
            new_leads: leads.filter((l) => l.status === "new").length,
            by_day: Object.entries(byDay).map(([date, count]) => ({ date, count })),
            by_site: bySite,
          };
        }),
        users: () => later(() => { requireUser("owner"); return load().users.map(publicUser); }),
        addUser: (b) => later(() => {
          requireUser("owner");
          if (!b.email || !b.name || !b.password || b.password.length < 8) throw new ApiError("Заполните e-mail, имя и пароль от 8 символов", 422);
          const db = load();
          const email = b.email.trim().toLowerCase();
          if (db.users.some((u) => u.email === email)) throw new ApiError("Пользователь с таким e-mail уже есть", 409);
          const u = { id: db.seq++, email, name: b.name, password: b.password, role: b.role || "staff", sites: b.sites ?? null };
          db.users.push(u);
          save(db);
          return publicUser(u);
        }),
        removeUser: (id) => later(() => {
          const me = requireUser("owner");
          if (Number(id) === me.id) throw new ApiError("Нельзя удалить самого себя", 422);
          const db = load();
          db.users = db.users.filter((u) => u.id !== Number(id));
          save(db);
          return null;
        }),
        exportLeads: (f = {}) => later(() => {
          const rows = scoped(load().leads, requireUser(), f.site).sort((a, b) => (a.created_at < b.created_at ? 1 : -1));
          const cell = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
          const lines = [["id", "Дата", "Сайт", "Тип", "Имя", "Телефон", "E-mail", "Комментарий", "Статус"].join(";")];
          for (const r of rows) lines.push([r.id, new Date(r.created_at).toLocaleString("ru-RU"), SITE[r.site].name, ...[r.kind, r.name, r.phone, r.email, r.message].map(csvSafe), r.status].map(cell).join(";"));
          return "﻿" + lines.join("\n");
        }),
      },

      // Изменения из других вкладок приходят через событие storage
      onChange(cb) {
        const h = (e) => { if (e.key === KEY) cb(); };
        addEventListener("storage", h);
        return () => removeEventListener("storage", h);
      },
      // Только для демо: «кухня» сама двигает заказ, пока его статус не поменяли руками в админке
      demoAdvanceOrder(id, next) {
        const db = load();
        const o = db.orders.find((x) => x.id === Number(id));
        if (!o || o.touched || o.status === "done" || o.status === "cancelled") return;
        o.status = next;
        save(db);
      },
      reset() { store.del(KEY); store.del(SESSION); load(); },
    };
  }

  const api = BASE ? remoteApi(BASE) : demoApi();
  api.SITES = SITES;
  api.ApiError = ApiError;

  // ---------- Помощники для форм на сайтах ----------

  // Блокирует кнопку на время отправки и показывает ошибку под ней. Ошибку пробрасывает дальше.
  api.submit = async (form, fn) => {
    const btn = form.querySelector('button[type="submit"], button:not([type])');
    let err = form.querySelector(".pf-error");
    if (!err) {
      err = Object.assign(document.createElement("p"), { className: "pf-error" });
      err.setAttribute("role", "alert");
      err.style.cssText = "color:#d92d20;font-size:14px;margin:6px 0 0;font-weight:500";
      (btn || form.lastElementChild).insertAdjacentElement("afterend", err);
    }
    err.textContent = "";
    const label = btn && btn.textContent;
    if (btn) { btn.disabled = true; btn.textContent = "Отправляем…"; }
    try {
      return await fn();
    } catch (e) {
      err.textContent = e.message || "Не удалось отправить";
      throw e;
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = label; }
    }
  };

  // Ссылка «посмотреть в админке» под сообщением об успехе (только в демо)
  api.adminLink = (view = "leads", root = "../../") => api.mode === "demo"
    ? `<a href="${root}admin/#${view}" target="_blank" rel="noopener" style="display:inline-block;margin-top:10px;color:inherit;text-decoration:underline;font-weight:600">Посмотреть в админке →</a>`
    : "";

  // Спрашивает имя и телефон в небольшом окне, запоминает их для следующих записей
  api.askContact = (title = "Ваши контакты") => new Promise((resolve, reject) => {
    let saved = {};
    try { saved = JSON.parse(localStorage.getItem("pf-contact")) || {}; } catch {}
    // Стили окна задаются явно: сброс margin на сайтах и тёмная тема страницы не должны его ломать
    if (!document.getElementById("pf-ask-css")) {
      const sample = document.querySelector(".btn");
      const accent = sample ? getComputedStyle(sample).backgroundColor : "#111";
      const accentText = sample ? getComputedStyle(sample).color : "#fff";
      const css = document.createElement("style");
      css.id = "pf-ask-css";
      css.textContent = `
        .pf-ask { color-scheme: light; margin: auto; inset: 0; position: fixed; border: 0; border-radius: 20px; padding: 26px; width: min(380px, calc(100% - 32px)); max-height: calc(100% - 32px);
          background: #fff; color: #14161a; font: 15px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; box-shadow: 0 40px 100px -20px rgba(0, 0, 0, .6); }
        .pf-ask[open] { animation: pf-ask-in .3s cubic-bezier(.2, .8, .2, 1); }
        .pf-ask::backdrop { background: rgba(10, 12, 16, .6); backdrop-filter: blur(4px); }
        @keyframes pf-ask-in { from { opacity: 0; transform: translateY(16px) scale(.97); } }
        .pf-ask form { display: grid; gap: 12px; margin: 0; }
        .pf-ask__title { font-size: 19px; font-weight: 700; padding-right: 36px; margin: 0; }
        .pf-ask__sub { color: #62666f; font-size: 14px; margin: -6px 0 4px; }
        .pf-ask input { width: 100%; box-sizing: border-box; margin: 0; padding: 13px 14px; border: 1.5px solid #d9dce2; border-radius: 12px; background: #fff; color: #14161a; font: 16px system-ui, sans-serif; outline: none; }
        .pf-ask input:focus { border-color: ${accent}; box-shadow: 0 0 0 3px color-mix(in srgb, ${accent} 25%, transparent); }
        .pf-ask__ok { margin: 4px 0 0; padding: 14px; border: 0; border-radius: 12px; background: ${accent}; color: ${accentText}; font: 600 15px system-ui, sans-serif; cursor: pointer; }
        .pf-ask__x { position: absolute; top: 14px; right: 14px; width: 34px; height: 34px; margin: 0; padding: 0; border: 0; border-radius: 50%; background: #f1f2f4; color: #14161a; font-size: 16px; cursor: pointer; }`;
      document.head.appendChild(css);
    }
    const dlg = document.createElement("dialog");
    dlg.className = "pf-ask";
    dlg.innerHTML = `<form method="dialog">
      <button class="pf-ask__x" value="cancel" formnovalidate aria-label="Закрыть">✕</button>
      <p class="pf-ask__title">${title}</p>
      <p class="pf-ask__sub">Оставьте контакты, и запись сохранится. В следующий раз заполнять не придётся.${api.mode === "demo" ? " Это демо: запись попадёт в демо-админку." : ""}</p>
      <input name="name" required placeholder="Имя" autocomplete="name" aria-label="Имя">
      <input name="phone" type="tel" required placeholder="Телефон" autocomplete="tel" aria-label="Телефон">
      <button class="pf-ask__ok" value="ok">Записаться</button>
    </form>`;
    document.body.appendChild(dlg);
    const f = dlg.querySelector("form");
    f.elements.name.value = saved.name || "";
    f.elements.phone.value = saved.phone || "";
    // Завершаем по отправке формы и по Esc, не дожидаясь события close: в фоновых вкладках оно может запаздывать
    let finished = false;
    const finish = (ok) => {
      if (finished) return;
      finished = true;
      const contact = { name: f.elements.name.value.trim(), phone: f.elements.phone.value.trim() };
      if (dlg.open) dlg.close();
      dlg.remove();
      if (!ok) return reject(new ApiError("Отменено", 0));
      try { localStorage.setItem("pf-contact", JSON.stringify(contact)); } catch {}
      resolve(contact);
    };
    f.addEventListener("submit", (e) => { e.preventDefault(); finish(!e.submitter || e.submitter.value === "ok"); });
    dlg.addEventListener("cancel", (e) => { e.preventDefault(); finish(false); });
    dlg.addEventListener("close", () => finish(dlg.returnValue === "ok"));
    dlg.showModal();
  });

  // ---------- Плашка «это демо» над формами ----------
  // Посетитель портфолио мог бы принять форму демо-стоматологии за настоящую и оставить заявку «в никуда»
  if (api.mode === "demo" && /\/projects\//.test(location.pathname) && !new URLSearchParams(location.search).has("embed")) {
    const css = document.createElement("style");
    css.textContent = `.pf-demo-note { display: block; margin: 0 0 12px; padding: 8px 12px; border-radius: 10px; font: 500 13px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif;
      background: rgba(127, 127, 127, .12); color: inherit; opacity: .85; text-align: left; }
      .pf-demo-note a { color: inherit; text-decoration: underline; font-weight: 700; }`;
    document.head.appendChild(css);
    const note = () => {
      const p = document.createElement("p");
      p.className = "pf-demo-note";
      p.innerHTML = 'Это демо: заявка попадёт в <a href="../../admin/" target="_blank" rel="noopener">демо-админку</a>. Заказать такой сайт — <a href="https://t.me/feyegetsu" target="_blank" rel="noopener">в Telegram</a>.';
      return p;
    };
    const mark = (root) => root.querySelectorAll && root.querySelectorAll("form").forEach((f) => {
      // Поиск и фильтры — не заявки; формы в окнах (dialog) помечаем тоже
      if (f.dataset.pfNote || f.matches("[role=search]") || f.querySelector('input[type="search"]') || f.closest(".pf-ask")) return;
      f.dataset.pfNote = "1";
      f.prepend(note());
    });
    const start = () => {
      mark(document);
      new MutationObserver((list) => list.forEach((m) => m.addedNodes.forEach((n) => n.nodeType === 1 && (n.tagName === "FORM" ? mark(n.parentNode || document) : mark(n))))).observe(document.body, { childList: true, subtree: true });
    };
    document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", start) : start();
  }

  // ---------- Демо продают сами себя ----------
  // 1) после заявки, брони или заказа всплывает то, что в ту же секунду увидел администратор в Telegram;
  // 2) кнопка «Хочу такой сайт» ведёт в калькулятор главной с уже выбранными пунктами;
  // 3) в подвале честная подпись, что компании и цифры вымышлены.
  const demoPage = /\/projects\/([\w-]+)\//.exec(location.pathname);
  if (demoPage && SITE[demoPage[1]]) {
    const slug = demoPage[1];
    const framed = window.top !== window || new URLSearchParams(location.search).has("embed");
    const esc = (v) => String(v ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
    const rubles = (n) => `${Number(n).toLocaleString("ru-RU")} ₽`;
    const short = (t, n = 90) => (t.length > n ? `${t.slice(0, n - 1)}…` : t);
    const css = document.createElement("style");
    css.textContent = `
      .pf-push { position: fixed; top: 16px; right: 16px; z-index: 2147483000; width: min(350px, calc(100% - 32px)); margin: 0; padding: 0; border: 0; background: none; text-align: left; cursor: pointer;
        font: 13px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; color: #e9ecf2; opacity: 0; transform: translateY(-18px); transition: opacity .35s, transform .45s cubic-bezier(.2, .8, .2, 1); }
      .pf-push.show { opacity: 1; transform: none; }
      .pf-push__cap { display: inline-block; margin: 0 0 8px; padding: 5px 12px; border-radius: 999px; background: #fff; color: #14161a; font-weight: 600; font-size: 12.5px; box-shadow: 0 8px 20px -10px rgba(0, 0, 0, .5); }
      .pf-push__card { display: flex; gap: 12px; padding: 13px 14px; border-radius: 18px; background: rgba(30, 34, 44, .96); border: 1px solid rgba(255, 255, 255, .1); box-shadow: 0 24px 50px -18px rgba(0, 0, 0, .7); backdrop-filter: blur(12px); }
      .pf-push__icon { flex-shrink: 0; width: 36px; height: 36px; border-radius: 50%; background: #229ed9; display: grid; place-items: center; }
      .pf-push__icon svg { width: 18px; height: 18px; fill: none; stroke: #fff; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
      .pf-push__body { min-width: 0; flex: 1; }
      .pf-push__top { display: flex; justify-content: space-between; gap: 8px; margin: 0 0 2px; color: #9aa3b5; font-size: 11.5px; }
      .pf-push__title { margin: 0; font-weight: 700; font-size: 14px; color: #fff; }
      .pf-push__line { margin: 2px 0 0; overflow-wrap: anywhere; }
      .pf-push__muted { margin: 2px 0 0; color: #9aa3b5; font-size: 12px; }
      .pf-want { position: fixed; left: 16px; bottom: 16px; z-index: 44; display: flex; align-items: center; max-width: calc(100% - 100px); border-radius: 999px; overflow: hidden;
        background: rgba(20, 22, 28, .92); color: #fff; border: 1px solid rgba(255, 255, 255, .14); box-shadow: 0 16px 34px -14px rgba(0, 0, 0, .6); backdrop-filter: blur(10px);
        font: 600 14px/1.2 system-ui, -apple-system, "Segoe UI", sans-serif; transform: translateY(0); transition: transform .35s cubic-bezier(.2, .8, .2, 1), opacity .3s; }
      .pf-want a { color: inherit; text-decoration: none; padding: 12px 16px; white-space: nowrap; text-transform: none; letter-spacing: normal; font: inherit; }
      .pf-want a:hover { background: rgba(255, 255, 255, .08); }
      .pf-want__back { color: rgba(255, 255, 255, .7) !important; border-right: 1px solid rgba(255, 255, 255, .14); }
      .pf-want__go { overflow: hidden; text-overflow: ellipsis; }
      .pf-want__short { display: none; }
      .pf-want.hide { transform: translateY(calc(100% + 30px)); opacity: 0; pointer-events: none; }
      .pf-fiction { margin: 14px auto 0; max-width: 1100px; padding: 0 20px; font: 12px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; opacity: .65; text-align: center; }
      @media (max-width: 520px) { .pf-want { left: 12px; bottom: 12px; font-size: 13px; } .pf-want a { padding: 11px 13px; } .pf-want__back span, .pf-want__long { display: none; } .pf-want__short { display: inline; } }
      @media (prefers-reduced-motion: reduce) { .pf-push, .pf-want { transition: none; } }`;
    document.head.appendChild(css);

    // Уведомление «что увидел администратор»
    let pushTimer;
    const showPush = ({ title, lines = [], muted = "" }) => {
      document.querySelector(".pf-push")?.remove();
      const el = document.createElement("button");
      el.type = "button";
      el.className = "pf-push";
      el.setAttribute("aria-label", "Закрыть уведомление");
      el.innerHTML = `<span class="pf-push__cap">А вот что в эту секунду увидел администратор</span>
        <span class="pf-push__card"><span class="pf-push__icon"><svg viewBox="0 0 24 24"><path d="M21 4 3 11l6 2 2 6 3-4 5 4 2-15z"/><path d="m9 13 8-6"/></svg></span>
        <span class="pf-push__body"><span class="pf-push__top"><b>Telegram · ${esc(SITE[slug].name)}</b><span>сейчас</span></span>
        <span class="pf-push__title" style="display:block">${esc(title)}</span>
        ${lines.filter(Boolean).map((l) => `<span class="pf-push__line" style="display:block">${esc(short(l))}</span>`).join("")}
        ${muted ? `<span class="pf-push__muted" style="display:block">${esc(muted)}</span>` : ""}</span></span>`;
      el.setAttribute("role", "status");
      document.body.appendChild(el);
      void el.offsetWidth;
      el.classList.add("show");
      const close = () => { el.classList.remove("show"); setTimeout(() => el.remove(), 400); };
      el.addEventListener("click", close);
      clearTimeout(pushTimer);
      pushTimer = setTimeout(close, 9000);
    };
    const who = (b) => [b.name, b.phone || b.email].filter(Boolean).join(" · ");
    const when = (iso) => {
      const [d, t] = String(iso || "").split("T");
      if (!d || !t) return "";
      const [, m, day] = d.split("-");
      return `${day}.${m} в ${t.slice(0, 5)}`;
    };
    const LEAD_TITLE = {
      table: "Новая бронь столика", consult: "Запись на консультацию", quiz: "Заявка с квиза", viewing: "Запрос на просмотр", repair: "Запись на ремонт",
      signup: "Новая регистрация", trial: "Запись на пробную тренировку", subscribe: "Новая подписка", class: "Запись на занятие",
      event: "Запись на событие", guestlist: "Гость в списке", certificate: "Заказ сертификата", party: "Запрос на банкет",
    };
    const details = (data) => Object.values(data || {}).filter((v) => typeof v === "string" || typeof v === "number").slice(0, 4).join(" · ");
    const wrap = (method, render) => {
      const orig = api[method];
      if (!orig) return;
      api[method] = async (site, body) => {
        const res = await orig(site, body);
        if (api.mode === "demo") { try { showPush(render(body || {}, res || {})); } catch {} }
        return res;
      };
    };
    wrap("createLead", (b) => ({ title: LEAD_TITLE[b.kind] || "Новая заявка", lines: [who(b), details(b.data) || b.message], muted: "Заявка уже в админке, статус «новая»" }));
    wrap("createBooking", (b) => ({ title: "Новая запись", lines: [[b.service || b.resource, when(b.starts_at)].filter(Boolean).join(" · "), who(b)], muted: "Время занято в расписании" }));
    wrap("createOrder", (b, r) => ({
      title: `Новый заказ №${r.id ?? ""}`,
      lines: [(r.items || b.items || []).map((i) => `${i.name || i.ref} ×${i.qty || 1}`).join(", "), [r.total != null ? rubles(r.total) : "", b.mode === "pickup" ? "самовывоз" : b.address].filter(Boolean).join(" · ")],
      muted: who(b),
    }));

    const start = () => {
      // Подпись о вымышленных данных — в каждом подвале
      const foot = [...document.querySelectorAll("footer")].pop();
      if (foot && !/вымышлен/i.test(foot.textContent)) {
        const p = document.createElement("p");
        p.className = "pf-fiction";
        p.textContent = "Демо-проект из портфолио: компании, адреса, отзывы и цифры вымышлены.";
        foot.appendChild(p);
      }
      if (framed || navigator.webdriver) return;
      // Плашка «демо» сверху съедала первый экран: её заменяет компактная кнопка внизу слева
      document.querySelectorAll(".demo-bar").forEach((el) => el.remove());
      const s = document.createElement("script");
      s.src = new URL("offers.js", SCRIPT_SRC || location.href).href;
      s.onload = () => {
        const O = window.PF_OFFERS;
        const cfg = O && O.projects[slug];
        if (!cfg) return;
        const q = O.quote(cfg);
        const what = cfg.type === "miniapp" ? "Хочу такое приложение" : cfg.type === "landing" ? "Хочу такой лендинг" : "Хочу такой сайт";
        const whatShort = cfg.type === "miniapp" ? "Хочу такое же" : "Хочу такой же";
        const bar = document.createElement("nav");
        bar.className = "pf-want";
        bar.setAttribute("aria-label", "Портфолио");
        bar.innerHTML = `<a class="pf-want__back" href="../../#works">←<span> Портфолио</span></a><a class="pf-want__go" href="${O.calcLink(slug)}"><span class="pf-want__long">${what}</span><span class="pf-want__short">${whatShort}</span> — ${O.rub(q.full)} →</a>`;
        document.body.appendChild(bar);
        // Пока открыта корзина или окно, кнопка не мешает; нижние кнопки сайта тоже не перекрываем
        const overlaps = (sel) => {
          // Место кнопки без учёта сдвига при скрытии, иначе она мигала бы: спряталась — перекрытия нет — показалась
          const b = { left: bar.offsetLeft, top: bar.offsetTop, right: bar.offsetLeft + bar.offsetWidth, bottom: bar.offsetTop + bar.offsetHeight };
          return [...document.querySelectorAll(sel)].some((el) => {
            const r = el.getBoundingClientRect();
            return r.width && r.left < b.right && r.right > b.left && r.top < b.bottom + 12 && r.bottom > b.top - 12;
          });
        };
        let syncTimer;
        const sync = () => {
          clearTimeout(syncTimer);
          syncTimer = setTimeout(() => bar.classList.toggle("hide", document.body.style.overflow === "hidden"
            || !!document.querySelector("dialog[open], .drawer.open, .drawer.on, .sheet.open, .sheet.on, .toast.show, .toast.on")
            || overlaps(".main-btn:not(.off)")), 60);
        };
        new MutationObserver(sync).observe(document.body, { attributes: true, childList: true, subtree: true, attributeFilter: ["class", "open", "style"] });
        addEventListener("scroll", sync, { passive: true });
        sync();
      };
      document.head.appendChild(s);
    };
    document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", start) : start();
  }

  window.PortfolioAPI = api;
})();
